from functools import lru_cache
from pathlib import Path
from typing import Optional


class CFG:

    @staticmethod
    def read_grammar(filename="cfg.txt") -> tuple[str, set[tuple[str, str]]]:
        path = Path(__file__).parent / filename
        with open(path) as f:
            lines = f.read().splitlines()

        # Now lines = ["# ...", "", "X > Yz", ...]
        lines = [
            line.replace(" ", "")
            for line in lines
            if not line.strip().startswith("#") and line.strip() != ""
        ]  # Discard empty lines, comment lines, and space characters
        # Now lines = ["X>Yz", ...]

        start_variable = None
        rules = set()
        for line in lines:
            assert (
                line.count(">") == 1
            )  # There must be a single arrow (i.e., ">" character) in each line.
            assert (
                line.index(">") == 1
            )  # There must be a single character on the left-hand side of the arrow.

            lhs = line[0]
            assert (
                "A" <= lhs <= "Z"
            )  # Left-hand side of the arrow must be a capital English letter.
            if start_variable is None:
                start_variable = lhs

            rhs = line[2:]
            alternatives = rhs.split("|")
            assert all(
                map(
                    lambda s: s == "|"
                    or "A" <= s <= "Z"
                    or "a" <= s <= "z"
                    or "0" <= s <= "9",
                    rhs,
                )
            )  # Right-hand side of the arrow must be an English letter, digit, or "|".
            for alternative in alternatives:
                rules.add((lhs, alternative))

        return start_variable, rules

    @staticmethod
    def _count_terminals(string: str) -> int:
        # We count terminals, not distinct terminals.
        # Digits and lowercase letters except "e" (epsilon) are counted.
        count = 0
        for s in string:
            if "0" <= s <= "9" or ("a" <= s <= "z" and s != "e"):
                count += 1
        return count

    @staticmethod
    def _count_variables(string: str) -> int:
        # We count variables, not distinct variables.
        count = 0
        for s in string:
            if "A" <= s <= "Z":
                count += 1
        return count

    @staticmethod
    def _find_leftmost_variable(string: str) -> str:
        for s in string:
            if "A" <= s <= "Z":
                return s
        assert False

    @staticmethod
    def _apply_rule(current_string: str, rule: tuple[str, str]) -> str:
        lhs, rhs = rule
        assert lhs in current_string
        return current_string.replace(lhs, rhs, 1)  # Replace only the first occurrence.

    @staticmethod
    def pretty_print_derivation(derivation: list[str], minimize: bool = True) -> None:
        if len(derivation) == 0:
            print("There is no derivation.")
        else:
            if minimize:
                # We can't find the shortest possible derivation here easily but we can eliminate the obviously-unnecessary steps.

                # If we have A -> x -> B -> x -> C, we can just say it is A -> x -> C.
                # Try for every string from right to left:
                #     If there are at least another occurrence of it:
                #         Remove this string and everything between it and the first occurrence of it.
                potentially_shorter_derivation = derivation.copy()
                for string in reversed(derivation):
                    if potentially_shorter_derivation.count(string) > 1:
                        first_idx = potentially_shorter_derivation.index(string)
                        last_idx = (
                            len(potentially_shorter_derivation)
                            - potentially_shorter_derivation[::-1].index(string)
                            - 1
                        )
                        potentially_shorter_derivation = (
                            potentially_shorter_derivation[:first_idx]
                            + potentially_shorter_derivation[last_idx:]
                        )
                derivation = potentially_shorter_derivation

            print(" -> ".join(derivation))

    @staticmethod
    def from_rules(start_variable: str, rules: set[tuple[str, str]]) -> "CFG":
        variables = set()
        terminals = set()

        for rule in rules:
            lhs, rhs = rule
            variables.add(lhs)
            for symbol in rhs:
                if symbol == "e" or "A" <= symbol <= "Z":
                    pass  # Variable or epsilon
                elif "a" <= symbol <= "z" or "0" <= symbol <= "9":
                    terminals.add(symbol)
                else:
                    assert False

        return CFG(variables, terminals, rules, start_variable)

    def __init__(
        self,
        variables: set[str],
        terminals: set[str],
        rules: set[tuple[str, str]],
        start_variable: str,
    ) -> None:
        # General restrictions
        assert start_variable in variables  # Start variable is a variable
        assert (
            len(variables.intersection(terminals)) == 0
        )  # Variables and terminals are disjoint

        # Our restrictions
        assert "e" not in terminals  # Let's use "e" for epsilon
        assert all(map(lambda s: "A" <= s <= "Z", variables))
        assert all(map(lambda s: "a" <= s <= "z" or "0" <= s <= "9", terminals))
        for rule in rules:
            lhs, rhs = rule
            assert lhs in variables
            for symbol in rhs:
                assert symbol in {"e"}.union(variables.union(terminals))

        # There must be at least one rule for each variable
        for variable in variables:
            for rule in rules:
                lhs, rhs = rule
                if variable == lhs:
                    break
            else:
                assert False

        self.variables = variables
        self.terminals = terminals
        self.rules = rules
        self.start_variable = start_variable

    @lru_cache(maxsize=None)
    def _find_rules(self, variable: str) -> set[tuple[str, str]]:
        assert variable in self.variables
        # appropriate_rules = {rule for rule in self.rules if rule[0] == variable}
        appropriate_rules = set()
        for rule in self.rules:
            if rule[0] == variable:
                appropriate_rules.add(rule)
        return appropriate_rules

    def leftmost_derive(
        self,
        current_string: str,
        string: str,
        max_variable_count_in_intermediate_strings: int = 64,
        pool: Optional[set[str]] = None,
        current_derivation: Optional[list[str]] = None,
    ) -> list[str]:
        # This function return the derivation as list of strings, or return an empty list if the derivation is not possible.

        # Python cannot handle mutable default values for arguments!
        if current_derivation is None:
            current_derivation = []
        if pool is None:
            pool = set()

        if current_string in pool:
            # Maybe we can derive string from current_string but current_string is already in one of the derivation search branches,
            # so returning False here doesn't change the final result.
            # If it is an earlier string in this branch, then it is also fine to return False here.
            # Because there is no need to revisit a string in a derivation.
            return []
        pool.add(current_string)

        # Intermediate strings can contain infinite number of variables.
        # We will handle this situation by limiting the number of variables in intermediate strings.
        # This means that sometimes this function will return False when it should actually return True.
        # Our grammars are not that complex. So this will not be a problem for us.
        if (
            self._count_variables(current_string)
            > max_variable_count_in_intermediate_strings
        ):
            return []

        current_string = current_string.replace("e", "")  # Remove epsilons.
        string = string.replace("e", "")  # Remove epsilons.

        assert len(string) == self._count_terminals(
            string
        )  # The string must consist of terminals only.

        # In the case of recursive structures, the search will continue forever.
        # To avoid this, we stop and return False if current_string has more terminals than string.
        # (Because we know that applying a rule of a CFG cannot decrease the number of terminals: there is no deleting.)
        # (Note: In the case of "unrestricted grammars", this is no longer true. However, here we have a CFG.)
        terminal_count = self._count_terminals(current_string)
        if terminal_count > len(string):
            return []

        # Repeat until no variables remain (i.e., current_string does not contain a capital letter):
        #     Select the left-most variable (i.e., first capital letter in current_string)
        #     Replace the variable with the right-hand sides of a rule that has the variable on its left-hand side.

        # When there are multiple such rules we need to compute all branches.

        if terminal_count == len(current_string):  # There are no more variables.
            if current_string == string:
                return current_derivation + [current_string]
            else:
                return []

        leftmost_variable = self._find_leftmost_variable(current_string)
        appropriate_rules = self._find_rules(leftmost_variable)

        for appropriate_rule in appropriate_rules:
            derivation = self.leftmost_derive(
                self._apply_rule(current_string, appropriate_rule),
                string,
                max_variable_count_in_intermediate_strings,
                pool,
                current_derivation + [current_string],
            )
            if len(derivation) != 0:
                return derivation

        return []

    def derive(
        self,
        current_string: str,
        string: str,
        max_variable_count_in_intermediate_strings: int = 64,
    ) -> list[str]:
        assert all(
            map(lambda s: "A" <= s <= "Z" or "a" <= s <= "z" or "0" <= s <= "9", string)
        )  # Current string must contain English letters and digits only.
        assert all(
            map(lambda s: s != "e", current_string)
        )  # We use "e" for epsilon, so do not include it in the current strings.

        assert all(
            map(lambda s: "a" <= s <= "z" or "0" <= s <= "9", string)
        )  # String must contain lowercase English letters and digits only.
        assert all(
            map(lambda s: s != "e", string)
        )  # We use "e" for epsilon, so do not include it in the strings.

        # There is a derivation if and only if there is a leftmost derivation!
        return self.leftmost_derive(
            current_string, string, max_variable_count_in_intermediate_strings
        )

    def generate(
        self, string: str, max_variable_count_in_intermediate_strings: int = 64
    ) -> list[str]:
        assert all(
            map(lambda s: "a" <= s <= "z" or "0" <= s <= "9", string)
        )  # String must contain lowercase English letters and digits only.
        assert all(
            map(lambda s: s != "e", string)
        )  # We use "e" for epsilon, so do not include it in the strings.

        # Being able to generate a string means, deriving that variable from the start variable:
        return self.derive(
            self.start_variable, string, max_variable_count_in_intermediate_strings
        )

    def perform_tests(
        self,
        some_strings_in_language: list[str],
        some_strings_not_in_language: list[str],
        max_variable_count_in_intermediate_strings: int = 64,
    ) -> None:
        assert (
            len(
                set(some_strings_in_language).intersection(some_strings_not_in_language)
            )
            == 0
        )  # A string can either be a member of the language or not.

        error_found = False
        for string in some_strings_in_language:
            derivation = self.generate(
                string, max_variable_count_in_intermediate_strings
            )
            if len(derivation) == 0:
                print(
                    f"It looks like the grammar is incorrect: '{string}' is said to be in the language but the grammar *cannot* generate it. You can try this grammar again with a larger max_variable_count_in_intermediate_strings. But are you sure the string is in the language?"
                )
                error_found = True
        for string in some_strings_not_in_language:
            derivation = self.generate(
                string, max_variable_count_in_intermediate_strings
            )
            if len(derivation) > 0:
                print(
                    f"It looks like the grammar is incorrect: '{string}' is said to be *not* in the language but the grammar can generate it. Are you sure it is in the language?"
                )
                error_found = True

        if not error_found:
            print("The grammar has passed all the tests.")


if __name__ == "__main__":
    # STEP 1: Define your grammar in "cfg.txt".
    start_variable, rules = CFG.read_grammar()
    cfg = CFG.from_rules(start_variable, rules)

    # Optional: Try some strings. See a derivation when possible.
    # CFG.pretty_print_derivation(cfg.generate("001011", max_variable_count_in_intermediate_strings=64))
    # CFG.pretty_print_derivation(cfg.generate("0110", max_variable_count_in_intermediate_strings=64))
    # CFG.pretty_print_derivation(cfg.generate("10", max_variable_count_in_intermediate_strings=64))

    # Note:
    # I implemented a depth-first search. As a result, derivations can be long.
    # pretty_print_derivation displays the list of intermediate strings as a single string with arrows,
    # and removes the repeating parts of the derivation!
    # One can modify leftmost_derive to perform breadth-first search and get the shortest possible derivation.

    # STEP 2: Test the CFG.
    some_strings_in_language = ["", "01", "001011"]
    some_strings_not_in_language = ["0110", "10", "0", "1"]
    cfg.perform_tests(
        some_strings_in_language,
        some_strings_not_in_language,
        max_variable_count_in_intermediate_strings=64,
    )
