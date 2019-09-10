Access control in the Document Management system
================================================

The purpose is to let the DMS act as a real-life management system for
the file handling of some small business.
The key concept, there, is the separation of access according to users
and groups.

Fact 1: Users, in general, must NOT see each other's documents, not even
their names (because they usually imply sensitive data, like eg. a doc:
"Acme Company's Patent 012356 about fooobars.odf" )
Fact 2: Users, sometimes, fail to comprehend complex ACL schemes, so we
owe to keep things simple, a main principle applied all over the place.
Fact 3: our system has both statically placed files and directories, as
well as dynamic (aka "resources" in our terminology) nodes.

We allow/limit the access based on 3 factors (fields):
  - The "owner" field, which holds the user that created or "owns" the
    file or directory.
  - The "group_ids" field, on directories, which specifieds group-wise
    access
  - The "company_id" field, for multi-company access rules [1]

[1] at multi-company setups, we may want the same file hierarchy to apply
to different companies, and also nodes to be company-specific in it.

Principle of "owner"
----------------------
Files or directories that have an empty "owner" field are public. All users
will be able to _read_ them. Only the OpenERP Administrator or specified 
groups, however, will be able to modify them!
Files or directories that have an "owner" are private. Only their users will
be able to read or modify (including delete) them.
By default, all user's files are created with "owner" field set, thus private.

Principle of "group_ids"
-------------------------
Directories that have any group ids set will only (apart from their owner)
allow members of these groups to read them.
Directories that are created into the above directories will initially inherit
(that is, copy) the group_ids of their parents, so that they also allow 
access to the same users.

Implementation note
---------------------
Most of the principles are applied through record rules (see ir.rule object),
so an administrator can actually readjust them.
In order to have logical "areas" of folders, where different policies apply
(like group folders, personal areas), default values for directories' owners
and group_ids can be tuned (through the 'set default' functionality of 
fields).

Summary
--------

Table of permissions and behavior

|| Type | Owner set | Groups set | Description                              ||
|| Public |    -    |     -      | Public-readable folders, admin can write ||
|| Group  |    -    |     X      | Group can read, write, delete in them    ||
|| Group-read | X   |     X      | Group can read[2], owner can write/delete ||
|| Private |   X    |     -      | Only owner can read, write, delete in.   ||

[2] hint: using a wide group, like "Internal users" at this setup creates the
    effect of public-readable folders, with write permission to a non-admin user.
