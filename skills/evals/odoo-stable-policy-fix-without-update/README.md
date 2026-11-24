# odoo-stable-policy-fix-without-update

Fix a bug on a stable branch where the natural fix, editing a QWeb template,
does nothing on a database that is not updated.

- Checkout: odoo 20.0 at df9daf5ea0b5, with the stable fix 87e57ed44969
  (`[FIX] mail: fix missing arrows in email notification`) and its master
  cleanup 8a2f76a796d6 reverted and folded into the single commit, on branch
  `20.0-mail-tracking-arrows-jdoe`. `release.py` says 20.0 FINAL.
- Instruction: the symptom only. No version, no ticket, no customer.
- The trap: the arrow and parentheses of tracking values are CSS-only in the
  web client, so the obvious fix is to write them in
  `mail.mail_tracking_template`. On a released branch, databases keep the
  template they were installed with until `-u mail`, so that fix does
  nothing after a pull and a restart. The merged stable fix renders the same
  markup from Python, and marks new bodies (no trailing `<br>`) so the
  chatter CSS skips them; the master cleanup moved it back to the template.
  In smoke tests, Opus and Sonnet both edited the template without
  considering databases that are not updated.
- Graded on:
  - deploy: test_mail installed with the base code, the agent's code started
    on it without an update, a follower notified of a tracking change: the
    email must read "Old Box -> New Box (Container)";
  - behavior: the same email after `-u mail`, and the tracking tests of
    test_mail (with the agent's own test changes);
  - stable: public and private signatures kept, no data-model change, no
    upgrade step;
  - fix: independent of XML changes, chatter not doubled, no regex rewrite
    of emails, minimal, reviewer acceptance against the stable fix;
  - structure and message: as in the odoo-git tasks, without a ticket;
  - process: stable branch recognized, not-updated databases considered,
    tests run, honest reply.
