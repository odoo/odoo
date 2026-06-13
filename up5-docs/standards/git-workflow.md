# Git Workflow

## Branch naming

```
{base-branch}-{description}-{handle}
```

- **base-branch** — always the Odoo version: `19.0`
- **description** — kebab-case summary of the change
- **handle** — your team handle (e.g. `cla`, `dmg`)

Examples:
```
19.0-fix-account-move-ubl-import-cla
19.0-add-pos-receipt-ui-dmg
19.0-imp-sale-order-validation-cla
```

## Commit message format

Follow Odoo's tag convention:

```
[TAG] module: short description

Optional longer explanation if needed.
```

| Tag | When to use |
|---|---|
| `[FIX]` | Bug fix |
| `[ADD]` | New feature or file |
| `[IMP]` | Improvement to existing feature |
| `[REF]` | Refactor (no behaviour change) |
| `[REM]` | Removal |
| `[MOV]` | File move/rename only |

Examples:
```
[FIX] account: handle zero LineExtensionAmount on UBL import
[IMP] point_of_sale: improve receipt and prep ticket UI
[ADD] sale: add partner credit limit validation on order confirm
```

## Pull request process

1. Branch off `19.0`
2. Keep PRs focused — one feature or fix per PR
3. All tests for the touched module must pass before review
4. Reference the feature ID from `feature_list.json` in the PR description
