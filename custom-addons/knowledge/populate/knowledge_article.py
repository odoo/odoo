# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import populate
from odoo.addons.base.models.ir_qweb_fields import nl2br
from odoo.addons.knowledge.populate import tools


class KnowledgeArticle(models.Model):
    _inherit = 'knowledge.article'
    _populate_dependencies = [
        'res.users',  # membership management
    ]
    # be careful that size only defines the amount of ROOT articles
    # there will be a lot more articles in the end, counting children
    # see underlying docstring in '_prepare_children_articles'
    # manual testing gives around 3000-4000 generated articles for "medium" size
    # (giving a bigger size also increases the amount of res.users we have for members config)
    # /!\ using "large" can take a very long time as we can't take advantage of the batching
    # because of parent / children relationship, everything is committed in one singular batch
    _populate_sizes = {
        'small': 5,  # will result in ~1.500
        'medium': 20,  # will result in ~5.000 records
        'large': 100,  # will result in ~27.000 records
    }

    def _populate(self, size):
        # create some dummy portal users as res.users populate only creates internal users
        self.env['res.users'].create([{
            'login': 'portal_user_knowledge_%i' % i,
            'email': 'portaluserknowledge%i@example.com' % i,
            'name': 'Portal User %i' % i,
            'groups_id': [
                (6, 0, [self.env.ref('base.group_portal').id]),
            ]
        } for i in range(self.env['res.users']._populate_sizes[size])])

        return super()._populate(size)

    def _populate_factories(self, depth=0):
        internal_partner_ids = self.env['res.users'].search([
            ('share', '=', False),
        ]).partner_id.ids
        shared_partner_ids = self.env['res.users'].search([
            ('share', '=', True),
        ]).partner_id.ids

        return self._populate_article_factories(depth, internal_partner_ids, shared_partner_ids)

    def _populate_article_factories(self, depth, internal_partner_ids, shared_partner_ids):
        random = populate.Random('articles')
        if depth == 0:
            names = populate.iterate(tools._a_title_root)
        elif depth == 1:
            names = populate.iterate(tools._a_title_top_level)
        elif depth == 2:
            names = populate.iterate(tools._a_title_leaf)
        else:
            names = populate.randomize(tools._a_title_low_level, seed=random.randint(1, 100))

        return {
            ('name', names),
            ('body', populate.randomize([
                nl2br('%s' % tuple(tools.a_body_content_lorem_ipsum[:1])),
                nl2br('%s %s' % tuple(tools.a_body_content_lorem_ipsum[:2])),
                nl2br('%s %s %s' % tuple(tools.a_body_content_lorem_ipsum[:3])),
            ])),
            ('child_ids', populate.compute(lambda *args, **kwargs: self._prepare_children_articles(depth, internal_partner_ids, shared_partner_ids))),
            ('icon', populate.randomize(['🗒️', '🤖', '⭐', '🚀', '🎉', '☕', '🏆', '🛫', '💰', '📫'])),
            ('internal_permission', populate.compute(lambda *args, **kwargs: self._generate_internal_permission(depth))),
            ('is_locked', populate.randomize([True, False], [0.02, 0.98], seed=random.randint(1, 100))),
            ('full_width', populate.randomize([True, False], [0.2, 0.8], seed=random.randint(1, 100))),
            ('article_member_ids', populate.compute(lambda random, values, **kwargs: self._prepare_member_ids(depth, values, internal_partner_ids, shared_partner_ids))),
            ('is_locked', populate.randomize([True, False], [0.02, 0.98])),
            ('full_width', populate.randomize([True, False], [0.2, 0.8])),
            # TODO add article items / fill some properties fields
            ('favorite_ids', populate.compute(lambda values, *args, **kwargs: self._prepare_favorites(values, internal_partner_ids, shared_partner_ids))),
        }

    def _prepare_favorites(self, values, internal_partner_ids, shared_partner_ids):
        """In Knowledge we offer the possibility for a user to set articles as favorites.
        To handle this in the model we have a table `knowledge.article.favorite` that stores every
        favorited article for each user.

        Every article has a chance to be the favorite of a user but it is more likely that user will add
        a root as a favorite than a child.
        Thus to prepare the favorites we will need some information:
         * Will the article be favorited by a user ?
         * Which user wants to add the article to its favorite ?

        Of course we do not want a lot of articles being favorited so the initial check will reject many of the attempts,
        but if we want to add some favorite_ids to an article then we will check how many users will add the article as
        favorite.
        This is how we will populate the table."""
        random = populate.Random('favorites')

        article_member_ids = values.get('article_member_ids', False)
        internal_permission = values.get('internal_permission', False)
        # 2% of the articles can be set as favorites
        can_be_favorite = random.choices([True, False], weights=[0.02, 0.98], k=1)[0] and (
            internal_permission or article_member_ids)
        if not can_be_favorite:
            return []

        admin_partner_id = self.env.ref('base.user_admin').partner_id.id

        # sampling some partners
        internals = random.sample(internal_partner_ids, k=min(random.randint(2, 10), len(internal_partner_ids)))
        externals = random.sample(shared_partner_ids, k=min(random.randint(2, 10), len(shared_partner_ids)))
        # 50% chance to force admin into the mix (easier for testing)
        if admin_partner_id not in internals and random.choices([True, False], weights=[0.5, 0.5], k=1)[0]:
            internals.append(admin_partner_id)

        # If there are article members, check their permissions, otherwise, all are favorites
        all_partners = internals + externals
        favorite_partner_ids, partners_to_check_access = ([], all_partners) if article_member_ids else (all_partners, [])

        for partner_id in partners_to_check_access:
            member_access = next(
                (
                    member[2]['permission']
                    for member in article_member_ids
                    if member[2]['partner_id'] == partner_id
                ),
                False
            )

            if member_access == 'none':
                continue  # specified no access for this partner -> pass

            if internal_permission == 'none' and not member_access:
                continue  # internal permission denies access -> pass

            favorite_partner_ids.append(partner_id)

        # sadly the knowledge.article.favorite model needs user_id, so we have to fetch them
        linked_users = self.env['res.users'].search([('partner_id', 'in', favorite_partner_ids)])
        user_per_partner = {
            user.partner_id.id: user
            for user in linked_users
        }

        return [(0, 0, {
            'user_id': user_per_partner[partner_id].id
        }) for partner_id in favorite_partner_ids]

    def _prepare_children_articles(self, depth, internal_partner_ids, shared_partner_ids):
        """ As knowledge.article is a bit meaningless without a parent / children configuration,
        this methods aims to fill-up child_ids recursively.

        As the regular populate only allows to specify the 'total amount of records' we want to
        create, and it does not handle parent / children relationship, we apply a specific logic for
        children articles.

        The idea is to always have children for root articles and then lower the chances of generating
        children as you go into higher 'depth', with a maximum of 5 levels in total.
        The amount of children is chosen randomly between 2 and 10.

        The code that generates values re-uses the '_populate_factories' method and increases the depth
        every time we loop. """
        random = populate.Random('childrenarticles')

        if depth > 4 or random.randint(1, depth + 1) != depth + 1:
            # higher depth means lower chance of having children articles
            # depth of 0 -> 100% (randint(1,1) needs to equal 1)
            # depth of 1 -> 50% (randint(1,2) needs to equal 2)
            # depth of 2 -> 33% (randint(1,2,3) needs to equal 3)
            # ...
            return []

        record_count = 0
        create_values = []
        field_generators = self._populate_article_factories(depth + 1, internal_partner_ids, shared_partner_ids)

        generator = populate.chain_factories(field_generators, self._name)
        for _i in range(random.randint(2, 10)):
            values = next(generator)
            values.pop('__complete')
            create_values.append((0, 0, values))
            record_count += 1

        return create_values

    def _generate_internal_permission(self, depth):
        random = populate.Random('internalpermission')
        if depth != 0:
            # we keep it simple and only set custom internal permission to root articles
            return False

        category = random.choices(['workspace', 'private'], weights=[0.9, 0.1], k=1)[0]
        if category == 'private':
            # private articles should be 'none' and handled at members level
            return 'none'

        # 80% will be write, 20% read
        return random.choices(['write', 'read'], weights=[0.8, 0.2], k=1)[0]

    def _prepare_member_ids(self, depth, values, internal_partner_ids, shared_partner_ids):
        random = populate.Random('members')
        private_member_values = []

        admin_partner_id = self.env.ref('base.user_admin').partner_id.id
        if values.get('internal_permission') == 'none':
            # private article -> keep it simple and assume that people will test with admin user
            # there will be one auto-generated private article for every user anyway (so size is already big)
            private_member_values = [(0, 0, {
                'partner_id': admin_partner_id,
                'permission': 'write'
            })]

        # we tweak the end range, so that the deeper you go, the less chance you have of having
        # members configuration
        randint = random.randint(1, (depth + 1) * 10)
        if randint > 4 and values.get('internal_permission') == 'write':
            # 60% base chance of not having member configuration
            # unless we don't have a 'write' internal permission, in which case we need members
            return private_member_values

        internal_partner_ids = random.sample(internal_partner_ids, k=min(random.randint(2, 10), len(internal_partner_ids)))
        members_values = []
        for partner_id in internal_partner_ids:
            if partner_id == admin_partner_id and private_member_values:
                continue  # avoid duplicate member

            # force one write members, otherwise 70% of write, 25% read, 5% none
            permission = 'write' if partner_id == internal_partner_ids[0] else random.choices(
                ['write', 'read', 'none'], weights=[70, 25, 5], k=1
            )[0]

            members_values.append({
                'partner_id': partner_id,
                'permission': permission
            })

        internal_member_ids = [
            (0, 0, member_values)
            for member_values in members_values
        ]

        if randint > 2 or values.get('internal_permission') == 'read':
            # 20% base chance of having only internal members
            return private_member_values + internal_member_ids

        # 10% base chance of having only external members
        shared_partner_ids = random.sample(shared_partner_ids, k=min(random.randint(2, 10), len(shared_partner_ids)))
        members_values = []
        for partner_id in shared_partner_ids:
            # 90% of write
            members_values.append({
                'partner_id': partner_id,
                'permission': random.choices(['read', 'none'], weights=[0.9, 0.1], k=1)[0]
            })

        shared_member_ids = [
            (0, 0, member_values)
            for member_values in members_values
        ]

        if randint == 2 and values.get('internal_permission') == 'write':
            # 10% base chance of having only external members (only for write internal permission)
            return shared_member_ids

        # 10% chance to have a mix of both
        return private_member_values + internal_member_ids + shared_member_ids
