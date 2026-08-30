# A Java byte code simulator (Python implementation)

## 1. Problem restatement, in plain terms

Build a tiny **stack-based virtual machine**. It reads a text program (one
instruction per line), holds it in memory, then executes it instruction by
instruction, using:

- an **operand stack** (max 10 values) — a scratch area every arithmetic
  and comparison instruction pushes to / pops from
- a **local variable array** (max 10 slots) — named storage, like local
  variables in a real program
- two custom instructions not in real Java byte code: `read` (take an
  int from the keyboard, push it) and `print` (pop the top value, print it)

The instruction subset: `ldc, iload, istore, iadd, isub, imul, idiv, ifeq,
iflt, ifgt, read, print`.

There is **no loop or if/else keyword** — only three conditional branches
that test the popped value against zero. Everything else has to be built
out of those three primitives.

## 2. Architecture

A program text file is parsed into a flat instruction list by an
**assembler**. A **program counter (`pc`)** then drives a fetch-decode-execute
loop: read the instruction at `pc`, execute it (which may push/pop the
stack, read/write a local slot, or redirect `pc` itself), advance, repeat
until `pc` runs past the end of the program.

```
 text file --> assembler --> instruction list --> [pc-driven execute loop]
                                                          |         |
                                                   operand stack   locals
```

## 3. Two constructs that make everything else possible

### 3.1 Unconditional jump ("goto"), synthesized

The instruction set has no `goto`. But:

```
ldc 0
ifeq target
```

pushes the constant `0`, then pops it and tests `== 0` — which is always
true. So this two-instruction idiom **always** jumps to `target`. Every
if/else and every loop in the sample programs is built with this trick
plus `iflt`/`ifgt`/`ifeq` for the actual conditions.

### 3.2 Labels instead of raw line numbers

Real byte code jump targets are numeric offsets, which are miserable to
hand-maintain (insert one instruction, renumber every jump below it). This
simulator's loader is a **two-pass assembler**: pass 1 scans the program
and records the instruction-index of every line ending in `label:`; pass 2
resolves every `ifeq/iflt/ifgt` target that names a label to its recorded
index (a target may also just be a raw integer — both are accepted). This
is the same idea a real assembler/linker uses to resolve symbols before
code runs.

## 4. Why task (b) — sorting — needs a different technique

`iload`/`istore` address a **fixed slot number baked into the
instruction itself**, exactly like real JVM byte code. There is no
instruction meaning "load the local variable whose index is currently on
top of the stack" — i.e. **no indirect / array addressing** exists in this
subset. So you cannot write the equivalent of `arr[i]` for a runtime
value of `i`.

The workaround: pick a fixed maximum `MAX_N` (7, chosen so the total slot
count stays within the default 10-slot limit) and **generate**, once, a
completely unrolled sequence of compare-and-swap instructions between
every pair of the `MAX_N` fixed slots — this is called a **sorting
network**. Slots beyond the actual input size `n` are padded with a large
sentinel value so they always sort to the end and are simply skipped when
printing (each read and each print is individually guarded by an `is this
position < n?` check built from the same three branch instructions).

`programs.py::generate_sort_program(max_n)` is a small Python function
that emits this network as byte code text — it is, itself, a miniature
"compiler" performing loop unrolling, the same technique real compilers
use when a target has no indirect addressing mode.

## 5. Code walkthrough (for when you need to extend it)

**`bytecode_simulator.py`**
- `BytecodeSimulator.load_program()` — the two-pass assembler described
  in §3.2. Produces `self.instructions`, a list of `[opcode, operand]`.
- `BytecodeSimulator.run()` — the fetch-execute loop. One big `if/elif`
  over `opcode`; each branch does the instruction's stack/locals effect
  and optionally sets `next_pc` to redirect control flow. **To add a new
  instruction**, add one more `elif` branch here and (if it takes an
  operand or is a branch) teach `load_program()` how to parse it.
- `_push`/`_pop` enforce the stack size bound and raise `BytecodeError`
  on overflow/underflow.
- `_java_idiv` reproduces Java's truncate-toward-zero integer division
  (Python's `//` floors instead, which differs on negative operands).

**`programs.py`**
- `PROGRAM_A` — static text implementing min/max of three numbers.
- `generate_sort_program(max_n)` — the sorting-network generator from §4.
- `PROGRAM_C` — static text implementing the 2x2 matrix sum.

**`test_simulator.py`** — plain-assert tests (no framework dependency):
core VM behaviour (arithmetic, overflow, the goto idiom, a hand-written
loop, Java-style division) plus multiple input cases for all three
required programs, including edge cases (ties, all-negative, empty input,
already-sorted, reverse-sorted). All 20 assertions currently pass.

## 6. If you're asked to add a feature later

Because the assembler already supports labels and the branch trio can
express any control flow, most extensions are additive:

- **New arithmetic op** (e.g. `imod`) — one `elif` in `run()`, add it to
  the no-operand opcode set in `load_program()`.
- **A new comparison** (e.g. `ifge`, "jump if ≥ 0") — combine the
  existing primitives: `ifgt target` then `ifeq target` covers `>0` or
  `==0`, i.e. `>=0`, without touching the VM at all.
- **Bigger programs** — `max_stack_size`/`max_locals_size` are
  constructor parameters; raise them if a program needs more room.
- **A true array/indirect-addressing instruction** — this is the one
  change that touches the VM's core: it would need a new opcode that
  pops an index off the stack and uses it to index into `self.locals`
  (or a separate array store) rather than reading a compile-time
  operand — a genuine departure from real JVM byte code's addressing
  model, so mention explicitly if you're asked to add it.

## 7. Test programs — sample runs

| Program | Input | Output |
|---|---|---|
| min/max (a) | `5 2 9` | `2` (min) then `9` (max) |
| min/max (a) | `-4 10 -4` | `-4` then `10` |
| sort (b) | `n=5` then `5 3 4 1 2` | `1 2 3 4 5` |
| sort (b) | `n=7` then `-3 5 -1 0 2 -8 7` | `-8 -3 -1 0 2 5 7` |
| matrix sum (c) | `1 2 3 4` (A) `5 6 7 8` (B) | `6 8 10 12` |

## 8. How to run it yourself

```bash
python bytecode_simulator.py program_a_minmax.bc      # then type 3 ints
python bytecode_simulator.py program_b_sort.bc         # then type n, then n ints
python bytecode_simulator.py program_c_matrix_sum.bc   # then type 8 ints (A then B)
python bytecode_simulator.py program_a_minmax.bc -v    # -v traces every instruction

python test_simulator.py    # runs all automated tests
```
