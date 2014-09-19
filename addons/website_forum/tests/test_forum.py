# -*- coding: utf-8 -*-
import openerp.tests
from openerp.exceptions import AccessError

class TestForum(openerp.tests.HttpCase):
    def test_forum(self):
        # Usefull models
        forum_post = self.env['forum.post'];
        forum_tag = self.env['forum.tag'];
        forum_forum = self.env['forum.forum'];
        res_users = self.env['res.users'];
        forum_post_reason = self.env['forum.post.reason'];
        
        # Group's
        group_public = self.env['ir.model.data'].xmlid_to_res_id('base.group_public')
        group_portal = self.env['ir.model.data'].xmlid_to_res_id('base.group_portal')

        forum =  forum_forum.create({
            'name': 'Forum',
        })

        post_reason =  forum_post_reason.create({
            'name': 'Not relevant or out dated',
        })

        user_emp_1 =  res_users.create({
            'name': 'Useremp1',
            'login': 'useremp1',
            'email': 'useremp1@example.com',
        })
        
        user_emp_2 =  res_users.create({
            'name': 'Useremp2',
            'login': 'Useremp2',
            'email': 'useremp2@example.com', 
        })
        
        # public user
        user_public = res_users.create({
            'name': 'public user',
            'login': 'public user',
            'email': 'public@example.com',
            'groups_id': [(6, 0, [group_public])]
        })

        # portal user
        user_portal = res_users.create({
            'name': 'portal user',
            'login': 'portal user',
            'email': 'portal@example.com',
            'groups_id': [(6, 0, [group_portal])]
        })
        
        # Post with public user
        with self.assertRaises(AccessError):
            forum_post.sudo(user_public.id).create({
                'name': " Question ?",
                'forum_id': forum.id,
            })
            
        # Post with portal user
        self.assertTrue(forum_post.sudo(user_portal.id).create({
                'name': " Question ?",
                'forum_id': forum.id,
            }))
        
        # Create 'Tags' 
        forum_tags = forum_tag.create({
            'name': 'Contract',
            'forum_id': forum.id,
        })

        # Post emp1 user Questions
        useremp1_que_bef_karma = user_emp_1.karma
        useremp1_ques = forum_post.sudo(user_emp_1.id).create({
            'name': "Questions ?",
            'forum_id': forum.id,
            'tag_ids': [(4,forum_tags.id)],
        })
        user_emp_1.refresh()
        useremp1_que_aft_karma = user_emp_1.karma
        self.assertTrue((useremp1_que_aft_karma - useremp1_que_bef_karma) ==  forum.karma_gen_question_new, "Karma earned for new questions not match.")

        # Post emp1 user Answer
        useremp1_ans = forum_post.sudo(user_emp_1.id).create({
            'forum_id': forum.id,
            'content': "Answers .",
            'parent_id': useremp1_ques.id,
        })

        # User emp1 upvote its question: not allowed
        useremp1_ques_create_uid = forum_post.sudo(user_emp_1.id).browse(useremp1_ques.id).create_uid.id
        self.assertTrue((useremp1_ques_create_uid == user_emp_1.id),"User emp1 upvote its question not allowed.")

        #User emp1 upvote its answer: not allowed
        useremp1_ques_create_uid = forum_post.sudo(user_emp_1.id).browse(useremp1_ans.id).create_uid.id
        self.assertTrue((useremp1_ques_create_uid == user_emp_1.id),"User emp1 upvote its answer not allowed.")

        #User emp2 comments emp1's question
        user_emp_2.write({'karma': forum.karma_comment_own})
        self.assertTrue((user_emp_2.karma >= forum.karma_comment_own) ,"User emp2 karma is not enough comment emp1's question.")
        comment_id = useremp1_ques.sudo(user_emp_2.id).message_post("Comments .", 'comment', subtype='mt_comment')

        #User emp1 converts the comment to an answer
        user_emp_1.write({'karma': forum.karma_comment_convert_all})
        self.assertTrue((user_emp_1.karma >= forum.karma_comment_convert_all) ,"User emp1 converts the comment to an answer is not enough karma")
        new_post_id = forum_post.sudo(user_emp_1.id).convert_comment_to_answer(comment_id)

        #User emp1 converts its answer to a comment
        forum_post.sudo(user_emp_1.id).convert_answer_to_comment(new_post_id)

        #Post emp2 user Answer
        useremp2_ans = forum_post.sudo(user_emp_2.id).create({
            'forum_id': forum.id,
            'content': "Answers .",
            'parent_id': useremp1_ques.id,
        })

        # User emp1 upvote emp2's User answer
        user_emp_1.write({'karma': forum.karma_gen_question_upvote})
        self.assertTrue((user_emp_1.karma >= forum.karma_upvote) ,"User emp1 karma is not enough upvote answer.")
        useremp1_upv_bef_karma = user_emp_1.karma
        useremp2_upv_bef_karma = user_emp_2.karma

        useremp2_ans.sudo(user_emp_1.id).vote(upvote=True)

        user_emp_1.refresh()
        user_emp_2.refresh()
        useremp1_upv_aft_karma = user_emp_1.karma
        useremp2_upv_aft_karma = user_emp_2.karma

        #check karma emp1 user
        self.assertEqual(useremp1_upv_bef_karma, useremp1_upv_aft_karma, "karma update for a user is wrong.")
        #check karma emp2 user
        self.assertTrue((useremp2_upv_aft_karma - useremp2_upv_bef_karma) ==  forum.karma_gen_answer_upvote, "karma gen answer upvote not match.")

        #Post emp1 accepts emp2's answer
        user_emp_1.write({'karma': forum.karma_answer_accept_own})
        self.assertTrue((user_emp_1.karma >= forum.karma_answer_accept_own) ,"User emp1 karma is not enough accept answer.")
        useremp1_accept_bef_karma = user_emp_1.karma
        useremp2_accept_bef_karma = user_emp_2.karma

        post = forum_post.sudo(user_emp_1.id).browse(useremp2_ans.id)
        post.sudo(user_emp_1.id).write({'is_correct': not post.is_correct})

        user_emp_1.refresh()
        user_emp_2.refresh()
        useremp1_accept_aft_karma = user_emp_1.karma
        useremp2_accept_aft_karma = user_emp_2.karma

        self.assertTrue((useremp1_accept_aft_karma - useremp1_accept_bef_karma) ==  forum.karma_gen_answer_accept, "karma gen answer accept not match.")
        self.assertTrue((useremp2_accept_aft_karma - useremp2_accept_bef_karma) ==  forum.karma_gen_answer_accepted, "karma gen answer accepted not match.")

        #User emp2 down vote User emp1 answer
        user_emp_2.write({'karma': forum.karma_downvote})
        self.assertTrue((user_emp_2.karma >= forum.karma_answer_accept_own) ,"User emp2 karma is not enough accept answer.")
        useremp1_downv_bef_karma = user_emp_1.karma
        useremp2_downv_bef_karma = user_emp_2.karma

        useremp1_ans.sudo(user_emp_2.id).vote(upvote=False)

        user_emp_1.refresh()
        user_emp_2.refresh()
        useremp1_downv_aft_karma = user_emp_1.karma
        useremp2_downv_aft_karma = user_emp_2.karma
        self.assertTrue((useremp1_downv_aft_karma - useremp1_downv_bef_karma) ==  forum.karma_gen_answer_downvote, "karma gen answer downvote not match.")
        self.assertEqual(useremp2_downv_bef_karma, useremp2_downv_aft_karma, "karma update for emp2 user is wrong.")

        #User emp1 edits its own post
        user_emp_1.write({'karma': forum.karma_edit_own})
        self.assertTrue((user_emp_1.karma >= forum.karma_edit_own) ,"User emp1 edit its own post karma is not enough.")
        useremp1_ans.sudo(user_emp_1.id).write({'content':"Edits ."})

        # User emp1 edits emp2's post
        user_emp_1.write({'karma': forum.karma_edit_all})
        self.assertTrue((user_emp_1.karma >= forum.karma_edit_all) ,"User emp1 edit emp2's post karma is not enough.")
        useremp2_ans.sudo(user_emp_1.id).write({'content': "Edits ."})

        #User emp1 closes its own post
        user_emp_1.write({'karma': forum.karma_close_own})
        self.assertTrue((user_emp_1.karma >= forum.karma_close_own) ,"User emp1 closes its own post karma is not enough.")
        useremp1_ques.sudo(user_emp_1.id).close(post_reason.id)

        #User emp1 closes emp2's post
        # Post emp2 user Questions
        useremp2_ques = forum_post.sudo(user_emp_2.id).create({
            'name': "Question ?",
            'forum_id': forum.id,
            'tag_ids': [(4,forum_tags.id)],
        })

        user_emp_1.write({'karma': forum.karma_close_all})
        self.assertTrue((user_emp_1.karma >= forum.karma_close_all) ,"User emp1 closes emp2's post karma is not enough.")
        useremp2_ques.sudo(user_emp_1.id).close(post_reason.id)

        #User emp1 delete its own post
        user_emp_1.write({'karma': forum.karma_unlink_own})
        self.assertTrue((user_emp_1.karma >= forum.karma_unlink_own) ,"User emp1 delete its own post karma is not enough.")
        useremp1_ques.sudo(user_emp_1.id).write({'active': False})

        #User emp1 delete emp2's post
        user_emp_1.write({'karma': forum.karma_unlink_all})
        self.assertTrue((user_emp_1.karma >= forum.karma_unlink_all) ,"User emp1 delete emp2's post karma is not enough.")
        useremp2_ques.sudo(user_emp_1.id).write({'active': False})
