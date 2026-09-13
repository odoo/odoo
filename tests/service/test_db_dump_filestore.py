import io
import os
import zipfile
from pathlib import Path

import pytest

from odoo.service.db.dump import _add_filestore_to_zip


def _pack(filestore: Path) -> dict[str, bytes]:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zipf:
        _add_filestore_to_zip(zipf, str(filestore))
        return {name: zipf.read(name) for name in zipf.namelist()}


@pytest.fixture
def filestore(tmp_path):
    """A filestore with a secret sitting just outside it."""
    secret = tmp_path / "SECRET.conf"
    secret.write_text("admin_passwd = $pbkdf2-sha512$notreally\n")
    store = tmp_path / "filestore"
    (store / "sub").mkdir(parents=True)
    (store / "normal.bin").write_bytes(b"real attachment")
    (store / "sub" / "nested.bin").write_bytes(b"nested attachment")
    return store, secret, tmp_path


class TestNothingOutsideTheFilestoreLeavesInABackup:
    """`_add_filestore_to_zip` decides what a downloadable backup contains.

    A symlink is the case that must be caught, and the asymmetry is the whole
    reason the check exists: creating a symlink does not require permission to
    READ its target, while `pg_dump`/the zip writer run as the Odoo service
    account, which usually can. So an attacker able to write into the filestore
    -- but not to read the server's config -- could otherwise plant a link and
    have the backup exfiltrate it for them.
    """

    def test_a_symlink_out_of_the_filestore_is_skipped(self, filestore):
        store, secret, _ = filestore
        (store / "innocuous.bin").symlink_to(secret)

        members = _pack(store)

        assert "filestore/innocuous.bin" not in members
        assert not any(b"admin_passwd" in blob for blob in members.values()), (
            "the secret's CONTENT reached the archive under some name; the "
            "backup now carries a file the requester could never read"
        )

    def test_a_symlink_to_a_directory_outside_is_not_descended(self, filestore):
        """Defended by `os.walk`'s default, not by the containment check.

        Verified by neutering the containment check: the two tests either side
        of this one go red, this one stays green, because `os.walk` does not
        follow directory symlinks unless asked. Both mechanisms would have to
        fail for this to leak -- `followlinks=True` alone would still be caught
        per-file -- and it is pinned here so that a future `followlinks=True`
        has to be a deliberate argument rather than a quiet one.
        """
        store, _, outside = filestore
        (outside / "elsewhere").mkdir()
        (outside / "elsewhere" / "loot.bin").write_bytes(b"outside data")
        (store / "shortcut").symlink_to(outside / "elsewhere")

        members = _pack(store)

        assert not any("shortcut" in name for name in members)
        assert not any(b"outside data" in blob for blob in members.values())

    def test_a_sibling_sharing_a_name_prefix_is_still_outside(self, filestore):
        """The check is component-wise, not a string prefix.

        `/x/filestore_evil/f` starts with `/x/filestore`, so a `startswith`
        test admits it. `os.path.commonpath` compares path COMPONENTS and
        answers `/x`, which is what rejects it. This is the classic way a
        containment check is written wrong, so it is pinned rather than
        assumed.
        """
        store, _, outside = filestore
        evil = outside / "filestore_evil"
        evil.mkdir()
        (evil / "loot.bin").write_bytes(b"prefix confusion")
        (store / "looks_local.bin").symlink_to(evil / "loot.bin")

        members = _pack(store)

        assert "filestore/looks_local.bin" not in members
        assert not any(b"prefix confusion" in blob for blob in members.values())

    def test_a_symlink_INSIDE_the_filestore_is_still_packed(self, filestore):
        """The guard must not over-reject: containment is the test, not linkhood.

        Odoo's own filestore deduplicates by checksum, so a legitimate store
        can hold links. Dropping them would silently ship an incomplete backup,
        which is worse than a noisy failure.
        """
        store, _, _ = filestore
        (store / "alias.bin").symlink_to(store / "normal.bin")

        members = _pack(store)

        assert members["filestore/alias.bin"] == b"real attachment"

    def test_ordinary_files_round_trip_with_filestore_relative_names(self, filestore):
        store, _, _ = filestore

        members = _pack(store)

        assert members["filestore/normal.bin"] == b"real attachment"
        assert members["filestore/sub/nested.bin"] == b"nested attachment"

    def test_a_missing_filestore_is_not_an_error(self, tmp_path):
        """A database that never stored an attachment still has to dump."""
        assert _pack(tmp_path / "never_created") == {}


def test_a_hardlink_is_not_in_scope_and_that_is_correct(filestore):
    """Recorded so nobody 'fixes' this into a false sense of protection.

    `realpath` cannot distinguish a hardlink from the file itself -- there is
    no indirection to resolve, both names ARE the inode -- so a hardlink into
    the filestore is packed. That is not a hole this function can or should
    close: with `fs.protected_hardlinks=1` (the default on this box and on
    every mainstream distro) a link may only be made to a file the caller
    already owns or can read and write, so anyone able to plant one could
    equally well have copied the bytes in. It grants no access, which is the
    only thing the symlink guard exists to deny.

    Detecting it would mean scanning the filesystem for other links to the same
    inode on every dumped file. The guard is aimed at the escalation, and the
    escalation is symlinks.
    """
    store, secret, _ = filestore
    os.link(secret, store / "hardlinked.conf")

    members = _pack(store)

    assert "filestore/hardlinked.conf" in members, (
        "if this ever starts being skipped, the reason will not be the "
        "containment check -- find out what changed before relying on it"
    )


def test_members_are_ordered_by_name_whatever_the_directory_listing_order(filestore):
    """Files of a directory first, then its subdirectories, each set sorted by
    name: the same dump twice yields the same member order."""
    store, _, _ = filestore
    for name in ("zz", "aa", "mm"):
        (store / name).mkdir()
        (store / name / "b.bin").write_bytes(b"b")
        (store / name / "a.bin").write_bytes(b"a")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zipf:
        _add_filestore_to_zip(zipf, str(store))
    assert zipfile.ZipFile(buf).namelist() == [
        "filestore/normal.bin",
        "filestore/aa/a.bin",
        "filestore/aa/b.bin",
        "filestore/mm/a.bin",
        "filestore/mm/b.bin",
        "filestore/sub/nested.bin",
        "filestore/zz/a.bin",
        "filestore/zz/b.bin",
    ]
