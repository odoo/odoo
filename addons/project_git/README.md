# project_git

Odoo 19 proof of concept for branch review directly on `project.task`.

## What it does

- uses `project.task` as the review object
- compares `source remote/branch` against `target remote/branch`
- renders the diff with an Owl field widget
- lets reviewers add inline comments directly from the diff
- stores the diff anchor on `mail.message`
- shows the same comments in the chatter and inline in the diff

## Git strategy

The module expects Odoo to run inside an existing git checkout.
It reads remote-tracking refs already available in that checkout.
It does **not** fetch from Odoo.

The compare command is:

```bash
git -c core.packedGitWindowSize=16m \
    -c core.packedGitLimit=128m \
    diff --no-color --no-ext-diff --find-renames --unified=3 --merge-base \
    <target_ref> <source_ref>
```

## Notes

This is still a POC. It focuses on a nicer review UI, not on merge execution.
