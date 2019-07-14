import odoo.tests


class TestFromURL(odoo.tests.TransactionCase):
    def test_youtube_urls(self):
        urls = {
            'W0JQcpGLSFw': [
                'https://youtu.be/W0JQcpGLSFw',
                'https://www.youtube.com/watch?v=W0JQcpGLSFw',
                'https://www.youtube.com/watch?v=W0JQcpGLSFw&list=PL1-aSABtP6ACZuppkBqXFgzpNb2nVctZx',
            ],
            'vmhB-pt7EfA': [  # id starts with v, it is important
                'https://youtu.be/vmhB-pt7EfA',
                'https://www.youtube.com/watch?feature=youtu.be&v=vmhB-pt7EfA',
                'https://www.youtube.com/watch?v=vmhB-pt7EfA&list=PL1-aSABtP6ACZuppkBqXFgzpNb2nVctZx&index=7',
            ],
            'hlhLv0GN1hA': [
                'https://www.youtube.com/v/hlhLv0GN1hA',
                'https://www.youtube.com/embed/hlhLv0GN1hA',
                'https://m.youtube.com/watch?v=hlhLv0GN1hA'
            ],
        }

        model = self.env['slide.slide']
        for id, urls in urls.items():
            for url in urls:
                with self.subTest(url=url, id=id):
                    document = model._find_document_data_from_url(url)
                    self.assertEqual(document[0], 'youtube')
                    self.assertEqual(document[1], id)
