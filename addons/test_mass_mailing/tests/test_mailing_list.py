from odoo.tests import tagged, users

from odoo.addons.mass_mailing.tests.common import MassMailCommon


@tagged('mailing_list')
class TestMailingListMerge(MassMailCommon):

    @users('user_marketing')
    def test_mailing_list_merge(self):
        """Check that merging correctly picks the destination, avoids duplicates and propagates opt-out."""
        src_list, dst_list, unrelated_list = self.env['mailing.list'].create([
            {'name': 'Source List'},
            {'name': 'Destination List'},
            {'name': 'Unrelated List'},
        ])
        mailing_src, mailing_dst, mailing_src_done = self.env['mailing.mailing'].create([
            {
                'contact_list_ids': (src_list + unrelated_list).ids,
                'state': 'draft',
                'subject': 'Mailing Draft Source List'
            }, {
                'contact_list_ids': dst_list.ids,
                'state': 'draft',
                'subject': 'Mailing Draft Destination List'
            }, {
                'contact_list_ids': src_list.ids,
                'state': 'done',
                'subject': 'Mailing Done Source List'
            }
        ])
        contact_pairs = [
            # exact duplicate
            (
                ({'email': 'same.contact.no.optout@test.lan', 'mobile': '+32468100001'}, [False]),
                ({'email': '"Same Contact" <same.contact.no.optout@test.lan>', 'mobile': '0468 100 001'}, [False]),
            ),
            (
                ({'email': 'same.contact.invalid', 'mobile': 'same.contact.invalid'}, [False]),
                ({'email': 'same.contact.invalid', 'mobile': 'same.contact.invalid'}, [False]),
            ),
            (
                ({'email': '', 'email_normalized': '', 'mobile': '', 'phone_sanitized': ''}, [False]),
                ({'email': False, 'email_normalized': False, 'mobile': False, 'phone_sanitized': False}, [False]),
            ),
            (
                ({'email': '"Same Email" <same.email.multi@test.lan>, same.email.multi.2@test.lan', 'mobile': '+32468100003'}, [False]),
                ({'email': 'same.email.multi@test.lan', 'mobile': '+32468100003'}, [False]),
            ),
            (
                ({'email': 'same.contact.src.optout@test.lan', 'mobile': '+32468100004'}, [True]),
                ({'email': 'same.contact.src.optout@test.lan', 'mobile': '+32468100004'}, [False]),
            ),
            (
                ({'email': 'same.contact.dst.optout@test.lan', 'mobile': '+32468100005'}, [False]),
                ({'email': 'same.contact.dst.optout@test.lan', 'mobile': '+32468100005'}, [True]),
            ),
            # all variations of same email + different phone
            (
                ({'email': 'same.email.src.phone@test.lan', 'mobile': '+32468200001'}, [False]),
                ({'email': 'same.email.src.phone@test.lan', 'mobile': ''}, [False]),
            ),
            (
                ({'email': 'same.email.dst.phone@test.lan', 'mobile': ''}, [False]),
                ({'email': 'same.email.src.phone@test.lan', 'mobile': '+32468200002'}, [False]),
            ),
            (
                ({'email': 'same.email.diff.invalid.phone@test.lan', 'mobile': 'same.email.diff.invalid.phone'}, [False]),
                ({'email': 'same.email.diff.invalid.phone@test.lan', 'mobile': 'same.email.diff.invalid.phone.two'}, [False]),
            ),
            (
                ({'email': 'same.email.diff.phone@test.lan', 'mobile': '+32468200003'}, [False]),
                ({'email': 'same.email.diff.phone@test.lan', 'mobile': '+32468200004'}, [False]),
            ),
            # all variations of same phone different emails
            (
                ({'email': 'src.email.same.phone@test.lan', 'mobile': '+32468300001'}, [False]),
                ({'email': '', 'mobile': '+32468300001'}, [False]),
            ),
            (
                ({'email': '', 'mobile': '+32468300002'}, [False]),
                ({'email': 'dst.email.same.phone@test.lan', 'mobile': '+32468300002'}, [False]),
            ),
            (
                ({'email': 'diff.email.multi@test.lan, diff.email.multi.1@test.lan', 'mobile': '+32468100003'}, [False]),
                ({'email': 'diff.email.multi.1@test.lan', 'mobile': '+32468100003'}, [False]),
            ),
            (
                ({'email': 'diff.email.invalid', 'mobile': '+32468100004'}, [False]),
                ({'email': '"Diff Email Invalid" diff.email.invalid', 'mobile': '+32468100004'}, [False]),
            ),
            (
                ({'email': 'diff.email.1.same.phone@test.lan', 'mobile': '+32468300005'}, [False]),
                ({'email': 'diff.email.2.same.phone@test.lan', 'mobile': '+32468300005'}, [False]),
            ),
            # Duplicates in source only
            (
                ([{'email': 'src.duplicate@test.lan', 'mobile': '+32468400001'}] * 2, [False] * 2),
                ([], []),
            ),
            (
                ([{'email': 'src.duplicate.one.optout@test.lan', 'mobile': '+32468400002'}] * 2, [True, False]),
                ([], []),
            ),
            # Duplicates in destination only
            (
                ([], []),
                ([{'email': 'dst.duplicate@test.lan', 'mobile': '+32468500001'}] * 2, [False] * 2),
            ),
            (
                ([], []),
                ([{'email': 'dst.duplicate.one.optout@test.lan', 'mobile': '+32468500002'}] * 2, [True, False]),
            ),
            # some varied contacts
            (
                ([{'email': f'diff.email.diff.phone.{n}@test.lan', 'mobile': '+32467' + '0' * (6 - len(str(n))) + str(n)} for n in range(120, 123)], [False] * 3),
                ([{'email': f'diff.email.diff.phone.{n}@test.lan', 'mobile': '+32467' + '0' * (6 - len(str(n))) + str(n)} for n in range(123, 130)], [False] * 6),
            ),
        ]
        contact_pairs = [
            ((self.env['mailing.contact'].create(create_vals_1), optout_vals_1), (self.env['mailing.contact'].create(create_vals_2), optout_vals_2))
            for ((create_vals_1, optout_vals_1), (create_vals_2, optout_vals_2)) in contact_pairs
        ]
        for (src_contacts, src_contact_optouts), (dst_contacts, dst_contact_optouts) in contact_pairs:
            src_list.contact_ids += src_contacts
            dst_list.contact_ids += dst_contacts
            (src_contacts + dst_contacts).invalidate_recordset(['subscription_ids'])
            for src_contact, src_contact_optout in zip(src_contacts, src_contact_optouts):
                src_contact.subscription_ids.opt_out = src_contact_optout
            for dst_contact, dst_contact_optout in zip(dst_contacts, dst_contact_optouts):
                dst_contact.subscription_ids.opt_out = dst_contact_optout

        contact_pairs = [(src_contacts, dst_contacts) for ((src_contacts, _), (dst_contacts, _)) in contact_pairs]

        # Duplicate shared between source list and another, should not remove contacts from the other list
        contact_all_lists, contact_all_lists_dup = self.env['mailing.contact'].create([{'email': 'src.used.in.other.list@test.lan', 'mobile': ''}] * 2)
        src_list.contact_ids += contact_all_lists_dup
        dst_list.contact_ids += contact_all_lists
        unrelated_list.contact_ids += contact_all_lists_dup

        # The same contact opted out in one list but not the other
        contact_shared_src_optout = self.env['mailing.contact'].create({'email': 'src.optout.shared@test.lan', 'mobile': ''})
        contact_shared_dst_optout = self.env['mailing.contact'].create({'email': 'dst.optout.shared@test.lan', 'mobile': ''})
        src_list.contact_ids += contact_shared_src_optout + contact_shared_dst_optout
        dst_list.contact_ids += contact_shared_src_optout + contact_shared_dst_optout
        (contact_shared_src_optout + contact_shared_dst_optout).invalidate_recordset(['subscription_ids'])
        contact_shared_src_optout.subscription_ids.filtered(lambda sub: sub.list_id == src_list).opt_out = True
        contact_shared_dst_optout.subscription_ids.filtered(lambda sub: sub.list_id == src_list).opt_out = True

        (
            contacts_duplicate_diff_phone_format,
            contacts_duplicate_invalid_formats,
            contacts_duplicate_empty_and_null,
            contacts_duplicate_multi_email,
            contacts_duplicate_optout_src,
            contacts_duplicate_optout_dst,
            contacts_same_email_src_phone,
            contacts_same_email_dst_phone,
            contacts_same_email_diff_phone_invalid,
            contacts_same_email_diff_phone,
            contacts_src_email_same_phone,
            contacts_dst_email_same_phone,
            contacts_diff_email_multi_same_phone,
            contacts_diff_email_invalid_same_phone,
            contacts_diff_email_same_phone,
            contacts_src_duplicates,
            contacts_src_duplicates_one_optout,
            contacts_dst_duplicates,
            contacts_dst_duplicates_one_optout,
            contacts_no_duplicates,
        ) = contact_pairs
        contacts = (src_list + dst_list + unrelated_list).contact_ids

        self.assertEqual(
            len(set(zip(dst_list.contact_ids.mapped('email'), dst_list.contact_ids.mapped('mobile')))),
            len(dst_list.contact_ids) - (
                (len(contacts_dst_duplicates[1]) - 1)
                + (len(contacts_dst_duplicates_one_optout[1]) - 1)
            ),
            "There should be exactly 2 duplicate pairs in the destination",
        )
        self.assertEqual(
            len(dst_list.subscription_ids.filtered('opt_out')),
            len(contacts_duplicate_optout_dst[1][0] + contacts_dst_duplicates_one_optout[1][0]),
        )

        original_dst_list_members = dst_list.contact_ids
        result_list = (src_list + dst_list).action_mailing_lists_merge()

        self.assertEqual(
            result_list['res_id'], dst_list.id,
            'The destination should be the one with the most recipients or most mailings and finally the oldest'
        )

        # Exact duplicates

        self.assertFalse(contacts_duplicate_diff_phone_format[0].exists())
        self.assertIn(contacts_duplicate_diff_phone_format[1], dst_list.contact_ids)

        self.assertFalse(contacts_duplicate_invalid_formats[0].exists(), "Same invalid emails and phones are the same contact.")
        self.assertIn(contacts_duplicate_invalid_formats[1], dst_list.contact_ids)

        self.assertFalse(contacts_duplicate_multi_email[0].exists(), "Whether some field is empty or null should not matter.")
        self.assertIn(contacts_duplicate_multi_email[1], dst_list.contact_ids)

        self.assertFalse(contacts_duplicate_multi_email[0].exists(), "Only the first email of multi is considered.")
        self.assertIn(contacts_duplicate_multi_email[1], dst_list.contact_ids)

        self.assertFalse(contacts_duplicate_optout_src[0].exists())
        self.assertIn(contacts_duplicate_optout_src[1], dst_list.contact_ids)
        self.assertFalse(contacts_duplicate_optout_src[1].subscription_ids.opt_out, "Destination 'opt_out' status wins for duplicates.")

        self.assertFalse(contacts_duplicate_optout_dst[0].exists())
        self.assertIn(contacts_duplicate_optout_dst[1], dst_list.contact_ids)
        self.assertTrue(contacts_duplicate_optout_dst[1].subscription_ids.opt_out, "Destination 'opt_out' status wins for duplicates.")

        # Email-only duplicates

        self.assertIn(contacts_same_email_src_phone[0], dst_list.contact_ids,
            "Duplicate of only one field is expected to be copied over. Even if the other is empty.")
        self.assertIn(contacts_same_email_src_phone[1], dst_list.contact_ids)
        self.assertEqual(contacts_same_email_src_phone[1].mobile, '')

        self.assertIn(contacts_same_email_dst_phone[0], dst_list.contact_ids,
            "Duplicate of only one field is expected to be copied over. Even if the other is empty.")
        self.assertIn(contacts_same_email_dst_phone[1], dst_list.contact_ids)
        self.assertEqual(contacts_same_email_dst_phone[1].mobile, '+32468200002')

        self.assertIn(contacts_same_email_diff_phone_invalid[0], dst_list.contact_ids,
            "Different invalid phones are different.")
        self.assertIn(contacts_same_email_diff_phone_invalid[1], dst_list.contact_ids)

        self.assertIn(contacts_same_email_diff_phone[0], dst_list.contact_ids)
        self.assertIn(contacts_same_email_diff_phone[1], dst_list.contact_ids)

        # Phone-only duplicates

        self.assertIn(contacts_src_email_same_phone[0], dst_list.contact_ids,
            "Duplicate of only one field is expected to be copied over. Even if the other is empty.")
        self.assertIn(contacts_src_email_same_phone[1], dst_list.contact_ids)

        self.assertIn(contacts_dst_email_same_phone[0], dst_list.contact_ids,
            "Duplicate of only one field is expected to be copied over. Even if the other is empty.")
        self.assertIn(contacts_dst_email_same_phone[1], dst_list.contact_ids)

        self.assertIn(contacts_diff_email_multi_same_phone[0], dst_list.contact_ids,
            "Only the first email of multi is considered.")
        self.assertIn(contacts_diff_email_multi_same_phone[1], dst_list.contact_ids)

        self.assertIn(contacts_diff_email_invalid_same_phone[0], dst_list.contact_ids,
            "Different invalid emails are different, even if similar.")
        self.assertIn(contacts_diff_email_invalid_same_phone[1], dst_list.contact_ids)

        self.assertIn(contacts_diff_email_same_phone[0], dst_list.contact_ids)
        self.assertIn(contacts_diff_email_same_phone[1], dst_list.contact_ids)

        # Duplicates in the source list

        self.assertTrue(contacts_src_duplicates[0] & dst_list.contact_ids)
        self.assertTrue(contacts_src_duplicates_one_optout[0] & dst_list.contact_ids)

        # Duplicates in the destination list

        self.assertEqual(contacts_dst_duplicates[1] & dst_list.contact_ids, contacts_dst_duplicates[1])
        self.assertEqual(contacts_dst_duplicates_one_optout[1] & dst_list.contact_ids, contacts_dst_duplicates_one_optout[1])

        # Regular non-duplicate contacts

        self.assertEqual((contacts_no_duplicates[0] + contacts_no_duplicates[1]) & dst_list.contact_ids, (contacts_no_duplicates[0] + contacts_no_duplicates[1]))

        self.assertEqual(
            dst_list.contact_ids, (
                original_dst_list_members
                + contacts_same_email_src_phone[0]
                + contacts_same_email_dst_phone[0]
                + contacts_same_email_diff_phone_invalid[0]
                + contacts_same_email_diff_phone[0]
                + contacts_src_email_same_phone[0]
                + contacts_dst_email_same_phone[0]
                + contacts_diff_email_multi_same_phone[0]
                + contacts_diff_email_invalid_same_phone[0]
                + contacts_diff_email_same_phone[0]
                + contacts_src_duplicates[0][1]
                + contacts_src_duplicates_one_optout[0][0]
                + contacts_no_duplicates[0]
            ),
        )
        self.assertTrue(dst_list.active)
        self.assertFalse(src_list.contact_ids, 'Source mailing list should be empty.')
        self.assertFalse(src_list.active)

        self.assertEqual(
            len(set(zip(dst_list.contact_ids.mapped('email'), dst_list.contact_ids.mapped('mobile')))),
            len(dst_list.contact_ids) - (
                (len(contacts_dst_duplicates[1]) - 1)
                + (len(contacts_dst_duplicates_one_optout[1]) - 1)
            ),
            'There should be no new duplicate in the contact info of the contacts.',
        )

        self.assertEqual(
            dst_list.subscription_ids.filtered('opt_out').contact_id,
            (
                contacts_src_duplicates_one_optout[0][0]
                + contacts_duplicate_optout_dst[1]
                + contacts_dst_duplicates_one_optout[1][0]
            ),
            (
                'Should be 1 opt-out from the source list (not originally present), 2 opt-outs from the destination list.'
                'Contacts that were already in the destination and not opted-out should remain not opted-out.'
            )
        )

        self.assertEqual(
            sorted((contacts - contacts.exists()).ids),
            sorted((
                contacts_src_duplicates[0][0]
                + contacts_src_duplicates_one_optout[0][1]
                + contacts_duplicate_diff_phone_format[0]
                + contacts_duplicate_invalid_formats[0]
                + contacts_duplicate_empty_and_null[0]
                + contacts_duplicate_multi_email[0]
                + contacts_duplicate_optout_src[0]
                + contacts_duplicate_optout_dst[0]
            ).ids),
            'Remaining duplicates in source lists should be deleted'
        )

        self.assertEqual(mailing_src.contact_list_ids, dst_list + unrelated_list,
            'Draft mailings should see merged lists replaced with the target of the merge.')
        self.assertEqual(mailing_src_done.contact_list_ids, src_list)
        self.assertEqual(mailing_dst.contact_list_ids, dst_list,
            'Done mailings should see their lists untouched regardless of merge result.')
