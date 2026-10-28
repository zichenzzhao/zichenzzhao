# Live audit ledger

**Status: WARN** · data as of 2026-10-28 03:00 ET · [run log](https://github.com/zichenzzhao/zichenzzhao/actions/runs/40647301550)

Source: GitHub `zichenzzhao/*` (fresh clone each run). Every number on the profile is recomputed from these exact commits by [`scripts/update_stats.py`](../scripts/update_stats.py). Repos are private; this ledger publishes counts and commit SHAs only.

## Commits audited

| Repo | Commit audited | Committed | All commits | Mine (counted) | Others' (excluded) | Mirror sync (excluded) | Merges (excluded) |
|---|---|---|--:|--:|--:|--:|--:|
| `abcd-engine` | `cf2ec8b` | 2026-10-26 | 5 | 2 | 0 | 3 | 0 |
| `aible_ABCD` | `2f9d647` | 2026-10-26 | 7 | 4 | 0 | 3 | 0 |
| `engineerhub` | `fc27677` | 2026-10-26 | 22 | 19 | 0 | 3 | 0 |
| `MAPLAB_Database` | `2c2afaf` | 2026-10-26 | 79 | 76 | 0 | 3 | 6 |
| `MAPLAB_MNE` | `802da35` | 2026-10-26 | 139 | 136 | 0 | 3 | 3 |
| `maplab_web` | `82891fc` | 2026-10-27 | 67 | 64 | 0 | 3 | 0 |
| `redcap-config` | `659b4eb` | 2026-10-26 | 6 | 3 | 0 | 3 | 0 |
| `ReMAP` | `00bae6b` | 2026-10-26 | 8 | 5 | 0 | 3 | 0 |
| `Synthetic_EEG_Cocaine` | `6401570` | 2026-10-26 | 38 | 35 | 0 | 3 | 0 |

## Where every line I added went

Only the first column is shown on the profile. A row reconciles when the buckets add up to the raw total.

| Repo | Raw lines added | Counted as code | Docs / config | Notebooks | Data / binary / lockfiles | Outputs / backups / assets | Generated | Colleague / vendored | Other file types | Reconciles |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|:-:|
| `abcd-engine` | 20,705 | 6,100 | 1,093 | 0 | 70 | 13,019 | 0 | 405 | 18 | ✅ |
| `aible_ABCD` | 89 | 79 | 1 | 0 | 3 | 3 | 0 | 0 | 3 | ✅ |
| `engineerhub` | 27,569 | 13,242 | 1,094 | 0 | 4,026 | 8,824 | 0 | 0 | 383 | ✅ |
| `MAPLAB_Database` | 116,506 | 82,772 | 8,431 | 0 | 6,346 | 17,091 | 234 | 0 | 1,632 | ✅ |
| `MAPLAB_MNE` | 7,940,826 | 56,852 | 10,829 | 5,842 | 315,208 | 6,666,606 | 0 | 884,823 | 666 | ✅ |
| `maplab_web` | 70,726 | 11,493 | 2,117 | 0 | 7,778 | 44,720 | 48 | 0 | 4,570 | ✅ |
| `redcap-config` | 898 | 464 | 409 | 0 | 0 | 0 | 0 | 0 | 25 | ✅ |
| `ReMAP` | 2,305 | 309 | 350 | 0 | 0 | 0 | 0 | 1,410 | 236 | ✅ |
| `Synthetic_EEG_Cocaine` | 1,132,330 | 0 | 546 | 84,555 | 5,002 | 1,039,699 | 0 | 0 | 2,528 | ✅ |

## Flags

- ⚠️ needs review `MAPLAB_Database`: commit `a389a91` (2026-10-06) adds 12,538 counted lines. Add `"MAPLAB_Database@a389a91": "reason"` to `stats/audit_acknowledged.json` once checked.
- ⚠️ needs review `MAPLAB_Database`: commit `be268a5` (2026-07-28) adds 10,308 counted lines. Add `"MAPLAB_Database@be268a5": "reason"` to `stats/audit_acknowledged.json` once checked.

## Rules

- **Mine** = non-merge commits whose author matches my names or emails, on every branch. Commits that only touch the account-mirroring workflow are housekeeping and excluded.
- **Counted as code** = lines added in source files. Excluded: docs and config, notebook diffs (notebooks count code-cell lines at HEAD instead), data, outputs, binaries, lockfiles, backups and archived copies, static asset dumps, files that declare themselves generated, and code supplied by colleagues or vendored.
- **Flags**: any single commit over 10,000 counted lines or any file over 3,000 lines is flagged until reviewed.
- **Status**: PASS = everything reconciles and every flag is reviewed. WARN = unreviewed flags. FAIL = a repo was unreachable or a ledger does not reconcile.

Fingerprint: `71c382a29fe7b017`
