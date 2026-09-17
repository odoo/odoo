from odoo import Command
from odoo.tests.common import tagged

from .test_document_common import TransactionCaseDocuments


@tagged("post_install", "-at_install")
class TestAccessPropagation(TransactionCaseDocuments):
    def _chain(self, name, root, mid, leaf, **kwargs):
        """A three-deep folder chain whose levels start at the given values."""
        Document = self.env["document.document"]
        folders = []
        parent = False
        for level in ("root", "mid", "leaf"):
            vals = {"name": f"{name}-{level}", "type": "folder"}
            vals.update(
                {"folder_id": parent.id} if parent else {"user_folder_id": "COMPANY"}
            )
            vals.update(kwargs if not parent else {})
            parent = Document.create(vals)
            folders.append(parent)
        self.env.flush_all()
        # Seeded past `action_update_access_rights`, so the starting state is
        # the one under test rather than one it produced.
        for folder, value in zip(folders, (root, mid, leaf), strict=True):
            self.env.cr.execute(
                "UPDATE document_document SET access_internal = %s WHERE id = %s",
                (value, folder.id),
            )
        self.env.invalidate_all()
        return folders

    def _values(self, folders):
        """The stored values, whoever holds the recordset.

        `sudo` because these assertions are about what propagation WROTE, not
        about who may read it -- and one of the fixtures below deliberately
        contains a folder its own creator can no longer reach.
        """
        self.env.invalidate_all()
        return [folder.sudo().access_internal for folder in folders]

    def test_a_root_already_at_the_value_still_propagates(self):
        """The seed was empty, so nothing happened at all."""
        folders = self._chain("A", "none", "edit", "edit")

        folders[0].action_update_access_rights(access_internal="none")

        self.assertEqual(self._values(folders), ["none", "none", "none"])

    def test_a_folder_already_at_the_value_does_not_cut_the_path(self):
        """The walk could not travel through it, so the leaf was unreachable."""
        folders = self._chain("B", "edit", "none", "edit")

        folders[0].action_update_access_rights(access_internal="none")

        self.assertEqual(self._values(folders), ["none", "none", "none"])

    def test_a_tree_that_differs_throughout_still_propagates(self):
        """Control: the case that always worked, so a regression names itself."""
        folders = self._chain("C", "edit", "edit", "edit")

        folders[0].action_update_access_rights(access_internal="none")

        self.assertEqual(self._values(folders), ["none", "none", "none"])

    def test_propagation_still_stops_at_a_folder_the_user_cannot_edit(self):
        """The edit filter stays on the walk, and it is not the same thing.

        Reaching past a folder the user cannot edit into its children would be a
        worse defect than the one this fixes, so the guard has its own test: the
        leaf here IS editable and must still be left alone, because the only
        path to it runs through a folder that is not.
        """
        Document = self.env["document.document"]
        user = self.env["res.users"].create(
            {
                "name": "Propagation User",
                "login": "propagation_user",
                "group_ids": [
                    Command.set([self.env.ref("document.group_documents_user").id])
                ],
            }
        )
        as_user = Document.with_user(user)
        root = as_user.create(
            {"name": "G-root", "type": "folder", "user_folder_id": "MY"}
        )
        mid = as_user.create({"name": "G-mid", "type": "folder", "folder_id": root.id})
        leaf = as_user.create({"name": "G-leaf", "type": "folder", "folder_id": mid.id})
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE document_document SET access_internal = 'none', owner_id = %s "
            "WHERE id = %s",
            (self.env.ref("base.user_admin").id, mid.id),
        )
        self.env.cr.execute(
            "DELETE FROM document_access WHERE document_id = %s AND partner_id = %s",
            (mid.id, user.partner_id.id),
        )
        self.env.cr.execute(
            "UPDATE document_document SET access_internal = 'edit' WHERE id = %s",
            (leaf.id,),
        )
        self.env.invalidate_all()
        # Asked by search, not by reading `user_permission` off the record: a
        # document this user cannot reach refuses the field read outright, so
        # the direct question is the one that cannot be asked.
        as_user_readable = Document.with_user(user).search(
            [("id", "in", (root | mid | leaf).ids)]
        )
        self.assertNotIn(mid, as_user_readable, "the middle folder is out of reach")
        self.assertIn(leaf, as_user_readable)
        self.assertEqual(leaf.with_user(user).sudo(False).user_permission, "edit")

        root.with_user(user).action_update_access_rights(access_internal="view")

        self.assertEqual(
            self._values([root, mid, leaf]),
            ["view", "none", "edit"],
            "the only path to the leaf runs through a folder this user cannot "
            "edit, so propagation must not arrive there",
        )

    def test_an_update_that_changes_nothing_queues_no_tracking(self):
        """The filter's real job, now done where it belongs.

        Widening the walk must not start reporting phantom changes: the UPDATE
        writes only rows whose value differs, so `RETURNING` yields nothing and
        the tracking queue -- and the cron trigger behind it -- stays untouched.
        """
        Tracking = self.env["document.access.tracking"]
        folders = self._chain("D", "view", "view", "view")
        folders[0].action_update_access_rights(access_internal="view")
        before = Tracking.sudo().search_count([])

        folders[0].action_update_access_rights(access_internal="view")

        self.assertEqual(Tracking.sudo().search_count([]), before)
