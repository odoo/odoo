import json
from odoo import http
from odoo.tests import RecordCapturer, tagged
from odoo.tests.common import HttpCase, new_test_user
from odoo.tools import file_open

@tagged('post_install', '-at_install')
class TestProjectSharingCoverImg(HttpCase):

    def setUp(self):
        super(TestProjectSharingCoverImg, self).setUp()
        self.portal_user = new_test_user(
            self.env,
            groups='base.group_portal',
            **({'login': 'portal_user'}),
        )
        self.task = self.env['project.task'].create({
            'name': 'Test Task',
        })
        self.authenticate(self.portal_user.login, self.portal_user.login)
        self.csrf_token = http.Request.csrf_token(self)

    def upload_attachment(self):
        """
            Helper method to upload an attachment and return its ID.

            This is NOT a test case because:
            - Uploading an image is a prerequisite for setting an image (`test_set_attachment`).
            - If this were a separate test case, the image would have to be uploaded twice
             (once for upload testing and again for image setup).
        """
        # Simulate a file upload
        with RecordCapturer(self.env['ir.attachment'].sudo(), []) as capture, \
             file_open('project/static/src/img/tasks_icon.png', 'rb') as file:
                file.seek(0)
                response = self.url_open(
                    '/project/controllers/upload_attachment',
                    files={'ufile': file},
                    data={
                        'csrf_token': self.csrf_token,
                        'model': 'project.task',
                        'id': self.task.id,
                    }
                )
        self.assertEqual(response.status_code, 200)
        response_str = response.content.decode('utf-8')

        # Use regex to extract the JSON data
        start_index = response_str.find('[{')
        end_index = response_str.find('}]') + 2 
        response_str = response_str[start_index:end_index]

        data = json.loads(response_str)
        self.assertIsNotNone(data,msg="json response not found")
        self.assertTrue(data[0]['filename'],msg="file name not found")
        self.assertEqual(data[0]['filename'], 'tasks_icon.png')
        return data[0]['id']

    def test_get_attachment(self,datalen= 0):
        """
            Test retrieving attachments for a given project task.

            Args:
                datalen (int): The expected number of attachments. Defaults to 0.

            This method sends a request to the '/project/controllers/get_attachment' endpoint
            to fetch attachments for the specified task. It then verifies that the number 
            of returned attachments matches the expected count.

            - Before uploading an attachment, it should return 0.
            - After uploading an attachment, it should return 1 (or more, if applicable).
        """
        response = self.url_open(
            '/project/controllers/get_attachment',
            data=json.dumps({
                'params':{
                    "model": "project.task",
                    "id": self.task.id, 
                    }}), 
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(
            len(data["result"]["attachments"]),
            datalen,
            msg=f"Expected {datalen} attachments, but got {len(data['result']['attachments'])}.Image retrieval failed."
            )

    def test_set_attachment(self):
        # Create an attachment
        attachment_id = self.upload_attachment()
        response = self.url_open(
            '/project/controllers/set_attachment',
            data=json.dumps({
                'params':{
                    "model": "project.task",
                    "field": "displayed_image_id",
                    "task_id": self.task.id, 
                    "attachment_id": attachment_id,
                    }}), 
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(
            data["result"]["status"],
            'success',
            msg=f"Failed to set the image. Expected status 'success'"
            )
        self.test_get_attachment(1)
