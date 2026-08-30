"""
Supported instructions (all operate on integers only):
    ldc <n>       push constant n
    iload <i>     push local variable slot i
    istore <i>    pop into local variable slot i
    iadd          pop b, pop a, push a+b
    isub          pop b, pop a, push a-b
    imul          pop b, pop a, push a*b
    idiv          pop b, pop a, push a/b (truncating toward zero, like Java)
    ifeq <target> pop a; if a == 0, jump to target
    iflt <target> pop a; if a <  0, jump to target
    ifgt <target> pop a; if a >  0, jump to target
    read          read one integer from input, push it (custom)
    print         pop the top value and print it(custom)



There is no "goto" in the instruction set. It is not needed --
``ldc 0`` followed by ``ifeq target`` always branches, since the
popped value is always 0. That two-instruction idiom is used
throughout the sample programs anywhere a plain unconditional jump
is required.
"""

from __future__ import annotations
from typing import List, Optional, Sequence


class BytecodeError(RuntimeError):
    """Raised for stack/locals bounds violations or malformed programs."""


class BytecodeSimulator:
    def __init__(
        self,
        max_stack_size: int = 10,
        max_locals_size: int = 10,
        input_values: Optional[Sequence[int]] = None,
        verbose: bool = False,
    ) -> None:
        self.max_stack_size = max_stack_size
        self.max_locals_size = max_locals_size
        self.stack: List[int] = []
        self.locals: List[int] = [0] * max_locals_size
        self.instructions: List[List] = []  # each entry: [opcode, operand_or_None]
        # If input_values is given, `read` pulls from this queue instead of stdin -- this is what makes the simulator unit-testable.
        self._input_queue: Optional[List[int]] = (
            list(input_values) if input_values is not None else None
        )
        self.printed: List[int] = []
        self.verbose = verbose

    def load_program(self, lines: Sequence[str]) -> None:
        """Two-pass assembler: pass 1 records label positions, pass 2
        resolves every branch target (label name or literal int) to a
        concrete instruction index."""
        raw_lines = []
        for line in lines:
            line = line.split("#", 1)[0].strip()  # strip comments
            if line:
                raw_lines.append(line)

        labels = {}
        instrs: List[List] = []
        for line in raw_lines:
            if line.endswith(":") and " " not in line:
                label_name = line[:-1]
                if label_name in labels:
                    raise BytecodeError(f"duplicate label '{label_name}'")
                labels[label_name] = len(instrs)
            else:
                parts = line.split()
                opcode = parts[0].lower()
                arg = parts[1] if len(parts) > 1 else None
                instrs.append([opcode, arg])

        branch_ops = {"ifeq", "iflt", "ifgt"}
        operand_ops = {"ldc", "iload", "istore"}
        for instr in instrs:
            opcode, arg = instr
            if opcode in branch_ops:
                if arg is None:
                    raise BytecodeError(f"{opcode} requires a target")
                instr[1] = labels[arg] if arg in labels else int(arg)
            elif opcode in operand_ops:
                if arg is None:
                    raise BytecodeError(f"{opcode} requires an operand")
                instr[1] = int(arg)
            elif opcode in {"iadd", "isub", "imul", "idiv", "read", "print"}:
                pass  # no operand
            else:
                raise BytecodeError(f"unknown opcode '{opcode}'")

        self.instructions = instrs

    @classmethod
    def from_file(cls, path: str, **kwargs) -> "BytecodeSimulator":
        with open(path) as f:
            lines = f.readlines()
        sim = cls(**kwargs)
        sim.load_program(lines)
        return sim


    def _push(self, value: int) -> None:
        if len(self.stack) >= self.max_stack_size:
            raise BytecodeError("operand stack overflow")
        self.stack.append(value)

    def _pop(self) -> int:
        if not self.stack:
            raise BytecodeError("operand stack underflow")
        return self.stack.pop()

    def _read_int(self) -> int:
        if self._input_queue is not None:
            if not self._input_queue:
                raise BytecodeError("input exhausted")
            return self._input_queue.pop(0)
        return int(input())

    @staticmethod
    def _java_idiv(a: int, b: int) -> int:
        """Java int division truncates toward zero (Python's // floors)."""
        q = abs(a) // abs(b)
        return -q if (a < 0) != (b < 0) else q


    def run(self) -> List[int]:
        pc = 0
        n = len(self.instructions)
        while pc < n:
            opcode, arg = self.instructions[pc]
            next_pc = pc + 1

            if opcode == "ldc":
                self._push(arg)
            elif opcode == "iload":
                if not (0 <= arg < self.max_locals_size):
                    raise BytecodeError(f"iload {arg} out of range")
                self._push(self.locals[arg])
            elif opcode == "istore":
                if not (0 <= arg < self.max_locals_size):
                    raise BytecodeError(f"istore {arg} out of range")
                self.locals[arg] = self._pop()
            elif opcode == "iadd":
                b, a = self._pop(), self._pop()
                self._push(a + b)
            elif opcode == "isub":
                b, a = self._pop(), self._pop()
                self._push(a - b)
            elif opcode == "imul":
                b, a = self._pop(), self._pop()
                self._push(a * b)
            elif opcode == "idiv":
                b, a = self._pop(), self._pop()
                if b == 0:
                    raise BytecodeError("division by zero")
                self._push(self._java_idiv(a, b))
            elif opcode == "ifeq":
                if self._pop() == 0:
                    next_pc = arg
            elif opcode == "iflt":
                if self._pop() < 0:
                    next_pc = arg
            elif opcode == "ifgt":
                if self._pop() > 0:
                    next_pc = arg
            elif opcode == "read":
                self._push(self._read_int())
            elif opcode == "print":
                v = self._pop()
                print(v)
                self.printed.append(v)
            else:
                raise BytecodeError(f"unknown opcode '{opcode}'")

            if self.verbose:
                print(
                    f"    [pc={pc:>3}] {opcode:<6} {arg if arg is not None else '':<4} "
                    f"stack={self.stack} locals={self.locals}"
                )
            pc = next_pc

        return self.printed


def main() -> None:
    import sys

    if len(sys.argv) < 2:
        print("usage: python bytecode_simulator.py <program_file> [-v]")
        sys.exit(0)
    verbose = "-v" in sys.argv
    sim = BytecodeSimulator.from_file(sys.argv[1], verbose=verbose)
    sim.run()


if __name__ == "__main__":
    main()
