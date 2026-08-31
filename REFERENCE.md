# Bytecode Reference Manual — testa.bc / testb.bc / testc.bc

VM model (from `bytecode_simulator.py`): one **Operand Stack** (LIFO, max 10
values) and one flat array of **Registers** (`self.locals`, max 10 slots,
addressed by a fixed compile-time integer — there is no indirect/array
addressing). There is no native `goto`; every unconditional jump in these
programs is the two-line idiom:

```
ldc 0
ifeq <target>     # pop the 0 we just pushed -> always true -> always jumps
```

Opcode cheat-sheet:

| Opcode | Stack effect | Notes |
|---|---|---|
| `ldc n` | push `n` | literal constant |
| `iload i` | push `R[i]` | read register, non-destructive |
| `istore i` | pop -> `R[i]` | write register, destructive pop |
| `iadd` | pop b, pop a, push `a+b` | |
| `isub` | pop b, pop a, push `a-b` | **first-pushed value is `a`** |
| `imul` / `idiv` | same pop order as `isub` | `idiv` truncates toward 0 |
| `ifeq/iflt/ifgt target` | pop a; jump if `a==0 / a<0 / a>0` | consumes the value either way |
| `read` | push value from input | |
| `print` | pop, print | |

---
## PROGRAM A — `testa.bc`  (Min/Max of 3 integers)

### Register Map
| Register | Meaning |
|---|---|
| R0 | input `a` |
| R1 | input `b` |
| R2 | input `c` |
| R3 | running `min` |
| R4 | running `max` |

### --- [BLOCK 1: READ INPUTS] --- (lines 1-6)
```
read              # Action: pull 1 int from input, push it        | Stack: [a]
istore 0          # Action: pop -> R0                              | Stack: []          | R0=a
read              # Action: pull 1 int, push it                    | Stack: [b]
istore 1          # Action: pop -> R1                              | Stack: []          | R1=b
read              # Action: pull 1 int, push it                    | Stack: [c]
istore 2          # Action: pop -> R2                              | Stack: []          | R2=c
```
**Scale-Up Formula:** to read N inputs instead of 3, repeat the `read` /
`istore <i>` pair once per input, incrementing `<i>` by 1 each time
(`istore 0, istore 1, istore 2, ... istore N-1`). N inputs consume N
registers, plus 2 more for `min`/`max` (Block 2) => you need
`max_locals_size >= N + 2` (default cap is 10, so N=3..8 fits without
touching the constructor; N=11 requires `BytecodeSimulator(max_locals_size=13)`).

### --- [BLOCK 2: INITIALIZE MIN/MAX FROM `a`] --- (lines 8-11)
```
iload 0           # Action: push R0 (a)                            | Stack: [a]
istore 3          # Action: pop -> R3 (min = a)                    | Stack: []          | R3=a
iload 0           # Action: push R0 (a) again                      | Stack: [a]
istore 4          # Action: pop -> R4 (max = a)                    | Stack: []          | R4=a
```
**Scale-Up Formula:** unchanged regardless of N — always seeds min/max from
the first input register (`iload 0`). No line count changes with scale.

### --- [BLOCK 3: `if (b < min) min = b`] --- (lines 13-23)
This is the "conditional-assign" idiom used 4 times in this program:
`cond -> ifTRUE jump to SET; else -> unconditional-goto join, skipping SET`.
```
iload 1           # Action: push R1 (b)                            | Stack: [b]
iload 3           # Action: push R3 (min)                          | Stack: [b, min]
isub              # Action: pop min, pop b, push b-min              | Stack: [b-min]
iflt set_min_b    # Action: pop (b-min); if <0 (b<min) jump ->SET   | Stack: []
ldc 0             # Action: (fell through, b>=min) push 0           | Stack: [0]
ifeq check_max_b  # Action: pop 0 -> always true -> goto join       | Stack: []
set_min_b:        # (label — landed on only if b<min)
iload 1           # Action: push R1 (b)                            | Stack: [b]
istore 3          # Action: pop -> R3  (min = b)                   | Stack: []          | R3=b
check_max_b:      # (join label — both paths land here)
```
**Scale-Up Formula:** to compare an extra variable `d` (register 5) against
`min`, copy this entire 11-line block, then:
- change every `iload 1` referring to the new variable to `iload 5`
- rename the 2 labels (`set_min_b`→`set_min_d`, `check_max_b`→`check_max_d`) to something unused
- insert the copied block immediately after the existing min/max checks for the previous variable

### --- [BLOCK 4: `if (b > max) max = b`] --- (lines 25-35)
Identical shape to Block 3, register/label names swapped and comparison flipped:
```
iload 1           # Action: push R1 (b)                            | Stack: [b]
iload 4           # Action: push R4 (max)                          | Stack: [b, max]
isub              # Action: pop max, pop b, push b-max              | Stack: [b-max]
ifgt set_max_b    # Action: pop (b-max); if >0 (b>max) jump ->SET   | Stack: []
ldc 0             # Action: (fell through) push 0                   | Stack: [0]
ifeq check_min_c  # Action: pop 0 -> always -> goto join            | Stack: []
set_max_b:
iload 1           # Action: push R1 (b)                            | Stack: [b]
istore 4          # Action: pop -> R4 (max = b)                    | Stack: []          | R4=b
check_min_c:
```

### --- [BLOCK 5: `if (c < min) min = c`] --- (lines 37-47)
Same as Block 3 with `iload 2` (c) in place of `iload 1` (b), labels `set_min_c` / `check_max_c`.

### --- [BLOCK 6: `if (c > max) max = c`] --- (lines 49-59)
Same as Block 4 with `iload 2` (c) in place of `iload 1` (b), labels `set_max_c` / `print_results`.

**Combined Scale-Up Formula for Blocks 3-6:** for each additional input
variable beyond `a`, copy **one min-block + one max-block** (22 lines
total), point every `iload` at the new register, and give the 4 labels
inside those two blocks unique names. Chain the final `ifeq` of the last
max-block to the program's `print_results` label (or to the next
variable's min-block if more remain).

### --- [BLOCK 7: PRINT RESULTS] --- (lines 60-64)
```
print_results:
iload 3           # Action: push R3 (min)                          | Stack: [min]
print             # Action: pop, print it                          | Stack: []
iload 4           # Action: push R4 (max)                          | Stack: [max]
print             # Action: pop, print it                          | Stack: []
```
**Scale-Up Formula:** unaffected by N — always prints the final R3 (min) then R4 (max).

### Function Swapping (Program A)
| Goal | Change |
|---|---|
| Track **max only** (drop min tracking) | Delete Block 3 (lines 13-23) and Block 5 (lines 37-47) entirely; retarget their surrounding jumps to skip straight to the next max-check. Print only `iload 4 / print`. |
| Track **min only** | Mirror: delete Block 4 and Block 6, print only `iload 3 / print`. |
| Find the value **closest to zero** instead of min | Before each `isub` comparison, take the absolute value of both operands first (needs new sub-sequence: push value, `ldc 0`, `isub`... i.e. `0 - x`, then compare that to `x` — no native `abs`, must be built from `iflt`+branch). Not a 1-line swap; flag as a structural change. |
| Reverse which branch is "the winner" in any block | Swap the comparison opcode: `iflt`↔`ifgt` (e.g. line 17 `iflt`→`ifgt` makes Block 3 behave like a max-check instead of a min-check). |

---
## PROGRAM C — `testc.bc`  (Element-wise sum of two 4-element vectors)

### Register Map
| Register | Meaning |
|---|---|
| R0-R3 | vector A, elements 0..3 |
| R4-R7 | vector B, elements 0..3 |
| R0-R3 (reused) | after Block 3, holds the **sum** A+B (in place) |

### --- [BLOCK 1: READ VECTOR A] --- (lines 1-8)
```
read              # Action: read int, push it                      | Stack: [A0]
istore 0          # Action: pop -> R0                               | Stack: []   | R0=A0
read              # Action: read int, push it                      | Stack: [A1]
istore 1          # Action: pop -> R1                               | Stack: []   | R1=A1
read              # Action: read int, push it                      | Stack: [A2]
istore 2          # Action: pop -> R2                               | Stack: []   | R2=A2
read              # Action: read int, push it                      | Stack: [A3]
istore 3          # Action: pop -> R3                               | Stack: []   | R3=A3
```

### --- [BLOCK 2: READ VECTOR B] --- (lines 10-17)
Identical pattern, filling R4-R7 with B0..B3.
```
read / istore 4   # R4=B0
read / istore 5   # R5=B1
read / istore 6   # R6=B2
read / istore 7   # R7=B3
```
**Scale-Up Formula (Blocks 1+2):** for a vector length N (instead of 4),
vector A occupies registers `0..N-1`, vector B occupies `N..2N-1`. Repeat
the `read`/`istore <i>` pair `2N` times total, `<i>` running `0,1,...,2N-1`.
Requires `max_locals_size >= 2N` (default 10 caps you at N=5 without
raising the constructor's `max_locals_size`).

### --- [BLOCK 3: ELEMENT-WISE ADD, IN PLACE] --- (lines 19-34)
One representative element (index 0), lines 19-22:
```
iload 0           # Action: push R0 (A0)                           | Stack: [A0]
iload 4           # Action: push R4 (B0)                           | Stack: [A0, B0]
iadd              # Action: pop B0, pop A0, push A0+B0              | Stack: [A0+B0]
istore 0          # Action: pop -> R0 (overwrite A0 with sum)      | Stack: []   | R0=A0+B0
```
The remaining three groups (lines 23-26, 27-30, 31-34) repeat this exactly,
walking the index pair `(1,5)`, `(2,6)`, `(3,7)`.

**Scale-Up Formula:** for element `k` of an N-element vector, emit
`iload k / iload (k+N) / iadd / istore k`. Loop `k` from `0` to `N-1`,
i.e. copy this 4-line group N times, each copy incrementing **both**
integers in the two `iload`s by 1 (the second `iload`'s offset from the
first is always `+N`) and incrementing the `istore` target by 1 to match
the first `iload`.

### --- [BLOCK 4: PRINT RESULT VECTOR] --- (lines 36-43)
```
iload 0 / print   # print R0 (A0+B0)
iload 1 / print   # print R1 (A1+B1)
iload 2 / print   # print R2 (A2+B2)
iload 3 / print   # print R3 (A3+B3)
```
**Scale-Up Formula:** repeat `iload k / print` for `k = 0..N-1`.

### Function Swapping (Program C)
| Goal | Change |
|---|---|
| Compute **A − B** instead of A + B | Change every `iadd` (lines 21, 25, 29, 33) to `isub`. Operand order is already correct: `isub` computes `(first iload) - (second iload)`, and A is loaded first in every group, so no reordering needed. |
| Compute **A × B** (element-wise) | Change every `iadd` to `imul`. |
| Compute **element-wise max(A,B)** instead of sum | Not a 1-opcode swap — replace each 4-line add group with the compare-and-swap-style idiom from Program A/B (`iload k; iload k+N; isub; ifgt <keepA>; ldc 0; ifeq <takeB>; <keepA>: iload k; ifeq/goto store; <takeB>: iload k+N; ...; istore k`), i.e. borrow Program B's compare pattern. |
| Leave B unread and add a constant instead | Delete Block 2 and replace `iload (k+N)` in Block 3 with `ldc <constant>`. |

---
## PROGRAM B — `testb.bc`  (Guarded read + sort a variable-length list, capacity 7)

This program is **generated code** (loop-unrolled by a Python "mini
compiler", per `EXPLANATION.md` §4) — it has no hand-written comments and
is ~470 lines of 3 mechanically repeated micro-patterns. Below, each
pattern is traced fully once; the rest are pointed out as exact repeats.

### Register Map
| Register | Meaning |
|---|---|
| R0 | `n` — actual element count, read first |
| R1-R7 | up to 7 data slots (real input if `slot index < n`, else sentinel `1000000000`) |
| R8 | scratch/temp register, used only during a swap |

### --- [BLOCK 1: READ COUNT `n`] --- (lines 1-2)
```
read              # Action: read int, push it                      | Stack: [n]
istore 0          # Action: pop -> R0                               | Stack: []   | R0=n
```

### --- [BLOCK 2: GUARDED FILL LOOP (unrolled ×7)] --- (lines 3-107)
Each iteration decides, for one fixed slot index `idx`, whether `idx < n`
(real data) or `idx >= n` (pad with a huge sentinel so it sorts to the
bottom and gets skipped on output). Traced for `idx = 0` (target register
1), lines 3-17:
```
ldc 0                # Action: push literal idx=0                   | Stack: [0]
iload 0              # Action: push R0 (n)                          | Stack: [0, n]
isub                 # Action: pop n, pop 0, push 0-n                | Stack: [-n]
iflt fill_real_0     # Action: pop (-n); if <0 (n>0, i.e. idx<n) jump -> fill_real_0 | Stack: []
ldc 0                # Action: (fell through: idx>=n) push 0        | Stack: [0]
ifeq fill_sentinel_0 # Action: pop 0 -> always true -> goto fill_sentinel_0 | Stack: []
fill_real_0:
read                 # Action: real element exists -> read it       | Stack: [x]
istore 1             # Action: pop -> R1                            | Stack: []   | R1=x
ldc 0                # Action: push 0 (to build unconditional jump) | Stack: [0]
ifeq after_fill_0    # Action: pop 0 -> always -> goto after_fill_0 | Stack: []
fill_sentinel_0:
ldc 1000000000       # Action: push sentinel constant               | Stack: [1e9]
istore 1             # Action: pop -> R1 (padding, no real input consumed) | Stack: [] | R1=1e9
after_fill_0:        # (join label)
```
The remaining 6 copies (lines 18-32, 33-47, 48-62, 63-77, 78-92, 93-107)
repeat this **verbatim pattern** for `idx = 1..6`, target register `2..7`.

**Scale-Up Formula:** to raise capacity from 7 slots to `MAX_N` slots,
copy this 15-line block `MAX_N` times. In copy number `idx` (0-based):
- the literal in the first `ldc <idx>` = `idx`
- the `istore`/target register in both the real and sentinel branch = `idx + 1`
- every label suffix (`fill_real_N`, `fill_sentinel_N`, `after_fill_N`) = `idx`
Registers used = `R0` (n) + `MAX_N` data slots + `R[MAX_N+1]` (swap temp,
see Block 3) ⇒ requires `max_locals_size >= MAX_N + 2`.

### --- [BLOCK 3: SORTING NETWORK — UNROLLED BUBBLE SORT ×21] --- (lines 108-401)
One compare-and-conditionally-swap unit, traced for the first pair
(registers 1,2), lines 108-121:
```
iload 1              # Action: push R1                              | Stack: [R1]
iload 2              # Action: push R2                              | Stack: [R1, R2]
isub                 # Action: pop R2, pop R1, push R1-R2            | Stack: [R1-R2]
ifgt swap_0_0        # Action: pop; if >0 (R1>R2, out of order) jump -> swap_0_0 | Stack: []
ldc 0                # Action: (fell through: already in order) push 0 | Stack: [0]
ifeq noswap_0_0      # Action: pop 0 -> always -> goto noswap_0_0    | Stack: []
swap_0_0:
iload 1              # Action: push R1 (old value)                  | Stack: [R1]
istore 8             # Action: pop -> R8 (temp = R1)                | Stack: []   | R8=R1(old)
iload 2              # Action: push R2                              | Stack: [R2]
istore 1             # Action: pop -> R1 (R1 = old R2)               | Stack: []   | R1=R2(old)
iload 8              # Action: push R8 (saved old R1)                | Stack: [R1old]
istore 2             # Action: pop -> R2 (R2 = old R1)               | Stack: []   | R2=R1(old) → registers 1,2 swapped
noswap_0_0:          # (join label)
```
This 14-line unit repeats 21 times total (lines 108-401), covering **6
descending-length passes** of a classic bubble sort over 7 elements:
pass 0 compares pairs `(1,2)(2,3)(3,4)(4,5)(5,6)(6,7)` — 6 units;
pass 1 compares `(1,2)...(5,6)` — 5 units; pass 2 — 4 units; pass 3 — 3
units; pass 4 — 2 units; pass 5 — 1 unit. Total `6+5+4+3+2+1 = 21`, i.e.
`C(7,2)` comparisons, the standard fully-unrolled bubble sort for 7
elements. Label suffixes are `swap_<pass>_<index>` / `noswap_<pass>_<index>`.

**Scale-Up Formula:** for `MAX_N` slots, emit `MAX_N - 1` passes; pass `p`
(0-indexed) contains `MAX_N - 1 - p` compare-swap units comparing
registers `(1+i, 2+i)` for `i = 0 .. MAX_N-2-p`. Copy the 14-line unit
`sum(1..MAX_N-1) = MAX_N*(MAX_N-1)/2` times total, incrementing the two
`iload`/`istore` register numbers per unit and giving each a unique
`swap_<pass>_<index>` / `noswap_<pass>_<index>` label pair. R8 (the temp
register) never changes.

### --- [BLOCK 4: GUARDED PRINT LOOP (unrolled ×7)] --- (lines 402-471)
Traced for slot index 0 (register 1), lines 402-411:
```
ldc 0                # Action: push literal idx=0                   | Stack: [0]
iload 0              # Action: push R0 (n)                          | Stack: [0, n]
isub                 # Action: pop n, pop 0, push 0-n                | Stack: [-n]
iflt do_print_0      # Action: pop (-n); if <0 (idx<n) jump -> do_print_0 | Stack: []
ldc 0                # Action: (fell through: idx>=n, padding slot) push 0 | Stack: [0]
ifeq skip_print_0    # Action: pop 0 -> always -> goto skip_print_0 | Stack: []
do_print_0:
iload 1              # Action: push R1 (sorted value)                | Stack: [R1]
print                # Action: pop, print it                        | Stack: []
skip_print_0:        # (join label — nothing printed if idx>=n)
```
The remaining 6 copies repeat this for `idx = 1..6`, register `2..7`.

**Scale-Up Formula:** copy this 10-line block `MAX_N` times; copy `idx`
uses literal `idx`, register `idx+1`, and label suffix `idx` — identical
pattern to Block 2's guard, minus the sentinel-fill half.

### Function Swapping (Program B)
| Goal | Change |
|---|---|
| **Descending** sort instead of ascending | Change every `ifgt` in the 21 compare-swap units (Block 3) to `iflt`. Also flip the padding sentinel in Block 2 from `ldc 1000000000` to `ldc -1000000000`, so padding still sorts to the unused end instead of contaminating the front. |
| Sort **strings/keys by a different field** | Not expressible — this VM only has one flat register file of ints; no records/structs, so nothing to swap for that. |
| Raise capacity beyond 7 | Apply the three Scale-Up Formulas above (Blocks 2, 3, 4) together, and raise `max_locals_size` to at least `MAX_N + 2`. |
| Use `>=`/`<=` instead of strict `>`/`<` for the swap test | Combine two branches: `ifgt swap` then (if that didn't jump) `ifeq swap` covers `>= 0`; needs 2 extra lines per unit, not a plain opcode substitution. |
