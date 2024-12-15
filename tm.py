from pathlib import Path


class TM:
    
    @staticmethod
    def read_machine(filename="tm.txt") -> tuple[str, set[tuple[str, str, str, str, str]]]:
        path = Path(__file__).parent / filename
        with open(path) as f:
            lines = f.read().splitlines()

        # Discard empty lines, comment lines, and space characters:
        lines = [
            line.replace(" ", "")
            for line in lines
            if not line.strip().startswith("#") and line.strip() != ""
        ]

        transitions = set()
        start_state = None

        for line in lines:
            assert line.count(":") == 2
            assert line.count(">") == 1
            assert line.index(":") < line.index(">") < line.rindex(":")

            source_state, read_write, destination = line.split(":")
            if start_state is None:
                start_state = source_state

            assert len(read_write) >= 3
            
            # 0, 1, x > x, l

            lhs, rhs = read_write.split(">")
            if "," in lhs:
                # There are multiple alternatives
                read_symbols = lhs.split(",")
            else:
                read_symbols = [lhs]

            if "," in rhs:
                # Write symbol is explicitly specified
                write_symbol, direction = rhs.split(",")
                write_symbols = [write_symbol] * len(read_symbols)
            else:
                write_symbols = read_symbols.copy()
                direction = rhs

            assert direction in {"l", "r"}

            for read_symbol, write_symbol in zip(read_symbols, write_symbols):
                transitions.add((source_state, read_symbol, write_symbol, direction, destination))

        assert start_state is not None
        return start_state, transitions

    @staticmethod
    def from_transitions(
        start_state: str,
        transitions: set[tuple[str, str, str, str, str]],
    ) -> "TM":
        states_except_reject_state = set()
        tape_alphabet = set()

        for source, read_symbol, write_symbol, direction, destination in transitions:
            states_except_reject_state.add(source)
            states_except_reject_state.add(destination)
            tape_alphabet.add(read_symbol)
            tape_alphabet.add(write_symbol)

        return TM(states_except_reject_state, tape_alphabet, transitions, start_state)

    def __init__(
        self,
        states_except_reject_state: set[str],
        tape_alphabet: set[str],
        transitions: set[tuple[str, str, str, str, str]],
        start_state: str,
        # We don't take input alphabet as input. Because tape_alphabet is sufficient and it is not possible to understand the input alphabet from a TM description.
        # We don't take the accept state as input. Because it is assumed to be "accept".
        # We don't take the reject state as input. Because it is implicit (all transitions not specified are reject transitions)
    ) -> None:
        # transitions is a set of 5-tuples (src, read, write, direction, dest)
        assert "." in tape_alphabet, "The tape alphabet must contain the blank symbol '.'"

        source_and_read_symbols = set()
        for source, read_symbol, write_symbol, direction, destination in transitions:
            assert source in states_except_reject_state, f"The source state '{source}' must be one of the states"
            assert destination in states_except_reject_state, f"The destination state '{destination}' must be one of the states"
            assert read_symbol in tape_alphabet, f"The read symbol '{read_symbol}' must be one of the tape alphabet symbols"
            assert write_symbol in tape_alphabet, f"The write symbol '{write_symbol}' must be one of the tape alphabet symbols"
            assert direction in {"l", "r"}, f"The direction '{direction}' must be 'l' or 'r'"

            # There cannot be two or more transitions with the same source state and read symbol.
            # There can be zero transitions with the same source state and read symbol. Because we omit reject transitions.
            assert (source, read_symbol) not in source_and_read_symbols, f"This is a deterministic TM. However, there are multiple transitions with the same source state '{source}' and read symbol '{read_symbol}'"
            source_and_read_symbols.add((source, read_symbol))

        assert start_state in states_except_reject_state, "The start state must be one of the states"
        assert "accept" in states_except_reject_state, "The accept state 'accept' must be one of the states"

        self.states_except_reject_state = states_except_reject_state
        self.tape_alphabet = tape_alphabet
        self.transitions = transitions
        self.start_state = start_state

    def _read_tape(self, tape: list[str], head: int) -> str:
        assert head >= 0
        if head >= len(tape):
            return "."
        return tape[head]
    
    def _write_tape(self, tape: list[str], head: int, symbol: str) -> None:
        if head >= len(tape):
            tape.extend("." * (head - len(tape) + 1))
        tape[head] = symbol

    def _simulate(self, tape: list[str], state: str, head: int) -> bool:
        if state == "accept":
            return True

        for transition in self.transitions:
            src, read, write, direction, dest = transition
            if src == state and self._read_tape(tape, head) == read:
                self._write_tape(tape, head, write)
                state = dest
                if direction == "r":
                    head += 1
                else:
                    head -= 1
                    if head < 0:
                        head = 0  # Prevent negative head
                
                break
        else:
            return False  # No transition was applicable, which means we are in a reject state

        return self._simulate(tape, state, head)


    def accepts(self, string: str) -> bool:
        return self._simulate(list(string), self.start_state, 0)

    def perform_tests(
        self,
        some_strings_in_language: list[str],
        some_strings_not_in_language: list[str],
    ) -> None:
        assert (
            len(
                set(some_strings_in_language).intersection(some_strings_not_in_language)
            )
            == 0
        )

        error_found = False
        for string in some_strings_in_language:
            if not self.accepts(string):
                print(
                    f"Error: '{string}' is in the language but rejected."
                )
                error_found = True
        for string in some_strings_not_in_language:
            if self.accepts(string):
                print(
                    f"Error: '{string}' is not in the language but accepted."
                )
                error_found = True

        if not error_found:
            print("All tests passed successfully.")


if __name__ == "__main__":
    start_state, transitions = TM.read_machine()
    tm = TM.from_transitions(start_state, transitions)

    # Test the Turing Machine
    some_strings_in_language = ["#", "11#11", "101#101", "000100#000100"]
    some_strings_not_in_language = ["1", "01", "1#0", "01#11", "0000#1111"]
    tm.perform_tests(some_strings_in_language, some_strings_not_in_language)
