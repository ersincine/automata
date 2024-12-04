from pathlib import Path


class NPDA:

    @staticmethod
    def read_automaton(
        filename="npda.txt",
    ) -> tuple[str, set[tuple[str, str, str, str, str]], set[str]]:
        path = Path(__file__).parent / filename
        with open(path) as f:
            lines = f.read().splitlines()

        # Process lines, discarding empty lines and comments.
        lines = [
            line.replace(" ", "")
            for line in lines
            if not line.strip().startswith("#") and line.strip() != ""
        ]

        transitions = set()
        start_state = None
        accept_states = set()

        assert len(lines) >= 1
        for line in lines[:-1]:
            assert line.count(":") == 2
            assert line.count(">") == 1
            assert line.index(":") < line.index(">") < line.rindex(":")

            source_state, label, destination_state = line.split(":")
            if start_state is None:
                start_state = source_state

            assert len(label) == 5
            assert label[1] == ","
            assert label[3] == ">"
            input_symbol, stack_pop, stack_push = label[0], label[2], label[4]

            transitions.add(
                (source_state, input_symbol, stack_pop, stack_push, destination_state)
            )

        accept_states = set(lines[-1].split(","))
        return start_state, transitions, accept_states

    @staticmethod
    def from_transitions_and_accept_states(
        start_state: str,
        transitions: set[tuple[str, str, str, str, str]],
        accept_states: set[str],
    ) -> "NPDA":
        states = set()
        input_alphabet = set()
        stack_alphabet = set()

        # Deduce states, input alphabet, and stack alphabet from transitions
        for source, input_symbol, stack_pop, stack_push, destination in transitions:
            states.update([source, destination])
            if input_symbol != "e":
                input_alphabet.add(input_symbol)
            if stack_pop != "e":
                stack_alphabet.add(stack_pop)
            if stack_push != "e":
                stack_alphabet.add(stack_push)

        return NPDA(
            states,
            input_alphabet,
            stack_alphabet,
            transitions,
            start_state,
            accept_states,
        )

    def __init__(
        self,
        states: set[str],
        input_alphabet: set[str],
        stack_alphabet: set[str],
        transitions: set[tuple[str, str, str, str, str]],
        start_state: str,
        accept_states: set[str],
    ) -> None:

        # Use "e" only for epsilon!

        # Each transition consists of these five values:
        # source state
        # input symbol or e (epsilon) to consume
        # stack symbol or e (epsilon) to pop
        # stack symbol or e (epsilon) to push
        # destination state

        assert start_state in states  # Start state must be a member of all states.
        assert (
            len(accept_states.difference(states)) == 0
        )  # Accept states must be a subset of all states.

        self.states = states
        self.input_alphabet = input_alphabet
        self.stack_alphabet = stack_alphabet
        self.transitions = transitions
        self.start_state = start_state
        self.accept_states = accept_states

    def _simulate(self, state: str, remaining_input: str, stack: str) -> bool:
        # Debugging output
        # print(f"Simulating: state={state}, remaining_input={remaining_input}, stack={stack}")

        # Base case: If we are in an accept state and input is consumed
        if state in self.accept_states and not remaining_input:
            return True

        # Recursive case: Explore all possible transitions from the current state
        for transition in self.transitions:
            source, input_symbol, stack_pop, stack_push, destination = transition

            # Ensure the transition is applicable
            if source != state:
                continue

            # Match input symbol (or handle epsilon transition)
            if (
                input_symbol != "e"
            ):  # If it's not epsilon, ensure it matches the next input symbol
                if not remaining_input or remaining_input[0] != input_symbol:
                    continue

            # Match stack symbol (or handle epsilon stack operation)
            if (
                stack_pop != "e"
            ):  # If it's not epsilon, ensure it matches the top of the stack
                if not stack or stack[-1] != stack_pop:
                    continue

            # Compute the new stack after this transition
            new_stack = stack[:-1] if stack_pop != "e" else stack
            if stack_push != "e":
                new_stack += stack_push

            # Compute the remaining input after this transition
            new_input = remaining_input[1:] if input_symbol != "e" else remaining_input

            # Recursively simulate the next state
            if self._simulate(destination, new_input, new_stack):
                return True

        # If no valid transition is found, return False
        return False

    def accepts(self, string: str) -> bool:
        """
        Determines if the given string is accepted by the NPDA.
        :param string: The input string to test.
        :return: True if the string is accepted, False otherwise.
        """
        return self._simulate(self.start_state, string, "")

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
        )  # A string can either be a member of the language or not.

        error_found = False
        for string in some_strings_in_language:
            if not self.accepts(string):
                print(
                    f"It looks like the NPDA is incorrect: '{string}' is said to be in the language but the NPDA rejects it. But are you sure the string is in the language?"
                )
                error_found = True
        for string in some_strings_not_in_language:
            if self.accepts(string):
                print(
                    f"It looks like the NPDA is incorrect: '{string}' is said to be *not* in the language but the NPDA accepts it. Are you sure it is in the language?"
                )
                error_found = True

        if not error_found:
            print("The NPDA has passed all the tests.")


if __name__ == "__main__":
    # STEP 1: Define your grammar in "npda.txt".
    start_state, transitions, accept_states = NPDA.read_automaton()
    npda = NPDA.from_transitions_and_accept_states(
        start_state, transitions, accept_states
    )

    # STEP 2: Test the NPDA.
    some_strings_in_language = ["", "01", "001011"]
    some_strings_not_in_language = ["0110", "10", "0", "1"]
    npda.perform_tests(some_strings_in_language, some_strings_not_in_language)

    # TODO: Display a path for accepted strings
    # TODO: Display the tree for rejected strings.
