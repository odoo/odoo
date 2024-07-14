# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase

class TestTags(TransactionCase):

    def test_create_tag(self):
        marketing_assets = self.ref('documents.documents_marketing_assets')
        tag = self.env['documents.tag'].create({
            'name': 'Foo',
            'facet_id': marketing_assets,
        })
        self.assertEqual(tag.facet_id.id, marketing_assets, 'should have the right facet')
        self.assertEqual(tag.name, 'Foo', 'should have the right name')
        self.assertTrue(tag.sequence > 0, 'should have a non-zero sequence')

    def test_get_tags(self):
        folder_id = self.ref('documents.documents_marketing_folder')
        facet_assets = self.env['documents.facet'].browse(self.ref('documents.documents_marketing_assets'))
        tag_assets_ads = self.env['documents.tag'].browse(self.ref('documents.documents_marketing_assets_ads'))
        tag_assets_videos = self.env['documents.tag'].browse(self.ref('documents.documents_marketing_assets_Videos'))

        domain = [('folder_id', '=', folder_id)]
        folder_ids = self.env['documents.folder'].search([('parent_folder_id', 'parent_of', folder_id)]).ids
        tags = self.env['documents.tag']._get_tags(domain, folder_ids)
        processed_tags = self.env['documents.document']._get_processed_tags(domain, folder_ids)
        self.assertEqual(processed_tags[0]['color_index'], 1, 'first record should have the right color index')
        self.assertEqual(len(tags), 4, 'should return a non-empty list of tags')

        first_record = {
            'group_id': facet_assets.id,
            'group_name': facet_assets.name,
            'group_sequence': facet_assets.sequence,
            'group_tooltip': None,
            'id': tag_assets_ads.id,
            'display_name': tag_assets_ads.name,
            'sequence': tag_assets_ads.sequence,
        }
        first_tag = tags[0]
        first_tag.pop('__count')
        self.assertEqual(tags[0], first_record, 'first record should match')

        last_record = {
            'group_id': facet_assets.id,
            'group_name': facet_assets.name,
            'group_sequence': facet_assets.sequence,
            'group_tooltip': None,
            'id': tag_assets_videos.id,
            'display_name': tag_assets_videos.name,
            'sequence': tag_assets_videos.sequence,
            '__count': 0,
        }
        self.assertEqual(tags[-1], last_record, 'last record should match')

    def test_get_tags_reordered(self):
        folder_id = self.ref('documents.documents_marketing_folder')
        facet_assets = self.env['documents.facet'].browse(self.ref('documents.documents_marketing_assets'))
        tag_assets_images = self.env['documents.tag'].browse(self.ref('documents.documents_marketing_assets_images'))
        tag_assets_videos = self.env['documents.tag'].browse(self.ref('documents.documents_marketing_assets_Videos'))

        tag_assets_images.sequence = 1

        domain = [('folder_id', '=', folder_id)]
        folder_ids = self.env['documents.folder'].search([('parent_folder_id', 'parent_of', folder_id)]).ids
        tags = self.env['documents.tag']._get_tags(domain, folder_ids)
        self.assertEqual(len(tags), 4, 'should return a non-empty list of tags')

        first_record = {
            'group_id': facet_assets.id,
            'group_name': facet_assets.name,
            'group_sequence': facet_assets.sequence,
            'group_tooltip': None,
            'id': tag_assets_images.id,
            'display_name': tag_assets_images.name,
            'sequence': tag_assets_images.sequence,
        }
        first_tag = tags[0]
        first_tag.pop('__count')
        self.assertEqual(first_tag, first_record, 'first record should match')

        last_record = {
            'group_id': facet_assets.id,
            'group_name': facet_assets.name,
            'group_sequence': facet_assets.sequence,
            'group_tooltip': None,
            'id': tag_assets_videos.id,
            'display_name': tag_assets_videos.name,
            'sequence': tag_assets_videos.sequence,
        }
        second_tag = tags[-1]
        second_tag.pop('__count')
        self.assertEqual(second_tag, last_record, 'last record should match')

    def test_get_tags_empty_folder(self):
        empty_folder_id = self.env['documents.folder'].create({
            'name': 'Empty Folder',
            'parent_folder_id': self.env.ref('documents.documents_marketing_folder').id,
        }).id
        facet_assets = self.env['documents.facet'].browse(self.ref('documents.documents_marketing_assets'))
        tag_assets_ads = self.env['documents.tag'].browse(self.ref('documents.documents_marketing_assets_ads'))
        tag_assets_videos = self.env['documents.tag'].browse(self.ref('documents.documents_marketing_assets_Videos'))

        domain = [('folder_id', '=', empty_folder_id)]
        folder_ids = self.env['documents.folder'].search([('parent_folder_id', 'parent_of', empty_folder_id)]).ids
        tags = self.env['documents.tag']._get_tags(domain, folder_ids)

        self.assertEqual(len(tags), 4, 'should return a non-empty list of tags')

        first_record = {
            'group_id': facet_assets.id,
            'group_name': facet_assets.name,
            'group_sequence': facet_assets.sequence,
            'group_tooltip': None,
            'id': tag_assets_ads.id,
            'display_name': tag_assets_ads.name,
            'sequence': tag_assets_ads.sequence,
            '__count': 0,
        }
        self.assertEqual(tags[0], first_record, 'first record should match')

        last_record = {
            'group_id': facet_assets.id,
            'group_name': facet_assets.name,
            'group_sequence': facet_assets.sequence,
            'group_tooltip': None,
            'id': tag_assets_videos.id,
            'display_name': tag_assets_videos.name,
            'sequence': tag_assets_videos.sequence,
            '__count': 0,
        }
        self.assertEqual(tags[-1], last_record, 'last record should match')