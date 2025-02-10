from odoo.tools import microdata as md
from odoo.tests import common


class TestMicrodata(common.TransactionCase):
    def test01_news_article(self):
        article = md.NewsArticle(
            headline="Title of a News Article",
            image=[
                "https://example.com/photos/1x1/photo.jpg",
                "https://example.com/photos/4x3/photo.jpg",
                "https://example.com/photos/16x9/photo.jpg"
            ],
            date_published=md.DateTime("2024-01-05T08:00:00+08:00"),
            date_modified=md.DateTime("2024-02-05T09:20:00+08:00"),
            author=[
                md.Person(name="Jane Doe", url="https://example.com/profile/janedoe123"),
                md.Person(name="John Doe", url="https://example.com/profile/johndoe123")
            ]
        )
        expected_dict = {
            '@context': 'https://schema.org/',
            '@type': 'NewsArticle',
            'image': ['https://example.com/photos/1x1/photo.jpg',
                    'https://example.com/photos/4x3/photo.jpg',
                    'https://example.com/photos/16x9/photo.jpg'],
            'author': [{'@type': 'Person',
                        'name': 'Jane Doe',
                        'url': 'https://example.com/profile/janedoe123'},
                        {'@type': 'Person',
                        'name': 'John Doe',
                        'url': 'https://example.com/profile/johndoe123'}],
            'dateModified': '2024-02-05T09:20:00+08:00',
            'datePublished': '2024-01-05T08:00:00+08:00',
            'headline': 'Title of a News Article'
        }
        generated_dict = article.to_dict()
        self.assertDictEqual(generated_dict, expected_dict, "Error in the expected article dictionary")
        self.assertEqual(article._validate_gsc(generated_dict), True, "The required properties should be there")

    def test02_breadcrumb_list(self):
        breadcrumb_list = md.BreadcrumbList(
            item_list_element=[
                md.ListItem(name="Books", position=1, item="https://example.com/books"),
                md.ListItem(name="Science Fiction", position=2, item="https://example.com/books/sciencefiction"),
                md.ListItem(name="Award Winners", position=3),
            ]
        )
        expected_dict = {
            '@context': 'https://schema.org/',
            '@type': 'BreadcrumbList',
            'itemListElement': [{'@type': 'ListItem',
                                 'name': 'Books',
                                 'position': 1,
                                 'item': 'https://example.com/books'},
                                {'@type': 'ListItem',
                                 'name': 'Science Fiction',
                                 'position': 2,
                                 'item': 'https://example.com/books/sciencefiction'},
                                {'@type': 'ListItem',
                                 'name': 'Award Winners',
                                 'position': 3}]}
        generated_dict = breadcrumb_list.to_dict()
        self.assertDictEqual(generated_dict, expected_dict, "Error in the expected breadcrumb_list dictionary")
        self.assertEqual(breadcrumb_list._validate_gsc(generated_dict), True, "The required properties should be there")

    def test03_course_info(self):
        course = md.Course(
            name="Learn Advanced C++ Topics",
            description="Improve your C++ skills by learning advanced topics.",
            publisher=md.Organization(name="CourseWebsite", url="www.examplecoursewebsite.com"),
            provider=md.Organization(name="Example University", url="www.ewample.com"),
            image=[
                "https://example.com/photos/1x1/photo.jpg",
                "https://example.com/photos/4x3/photo.jpg",
                "https://example.com/photos/16x9/photo.jpg"
            ],
            aggregate_rating=md.AggregateRating(rating_value=4, rating_count=1234, review_count=450),
            offers=[md.Offer(
                category=md.OfferCategory.Paid,
                price_currency="EUR",
                price=10.99,
                availability=md.ItemAvailability.InStock
            )],
            total_historical_enrollment=12345,
            date_published=md.Date("2024-03-21"),
            educational_level=md.EducationalLevel.Advanced,
            about=['C++ Coding', 'Backend Engineering'],
            teaches=['Practice and apply systems thinking to plan for change', 'Understand how memory allocation works.'],
            financial_aid_eligible='Scholaship Available',
            in_language="en",
            available_language=['fr', 'es'],
            syllabus_sections=[
                md.Syllabus(
                    name="Memory Allocation",
                    description="Learn how memory is allocated when creating C++ variables.",
                    time_required=md.Duration.from_components(num_hours=6)
                ),
                md.Syllabus(
                    name="C++ Pointers",
                    description="Learn what C++ pointer is and when they are used.",
                    time_required=md.Duration.from_components(num_hours=11)
                )
            ],
            review=[
                md.Review(
                    author=md.Person(name="Lou S."),
                    date_published=md.Date('2024-08-31'),
                    review_rating=md.Rating(rating_value=6, best_rating=10)
                )
            ],
            course_prerequisites=[
                'Basic understanding of C++ up to arrays and functions.',
                'https://www.example.com/beginnerCpp'
            ],
            educational_credential_awarded=[
                md.EducationalOccupationalCredential(
                    name='CourseProvider Certificate',
                    url="www.example.com",
                    credential_category=md.CredentialCategory.Certificate,
                    offers=[
                        md.Offer(
                            availability=md.ItemAvailability.InStock,
                            price=5,
                            price_currency='USD',
                            category=md.OfferCategory.Paid
                        )
                    ]
                )
            ],
            video=md.VideoObject(
                name='Video name',
                description='A video previewing this course',
                upload_date=md.DateTime('2024-03-28T08:00:00+08:00'),
                content_url='www.example.com/mp4',
                thumbnail_url=['www.example.com/thumbnailurl.jpg']
            ),
            has_course_instance=[
                md.CourseInstance(
                    course_mode=md.CourseMode.Blended,
                    location='Example University',
                    course_schedule=md.Schedule(
                        duration=md.Duration.from_components(num_hours=3),
                        repeat_frequency=md.RepeatFrequency.Daily,
                        repeat_count=31,
                        start_date=md.Date('2024-07-01'),
                        end_date=md.Date('2024-07-31')
                    ),
                    instructor=md.Person(
                        name='Ira D.',
                        description='Professor at X-University',
                        image='http://example.com/person.jpg'
                    )
                ),
                md.CourseInstance(
                    course_mode=md.CourseMode.Online,
                    course_workload=md.Duration.from_components(num_days=2)
                )
            ],
            has_part=[
                md.Course(
                    name='C++ Algorithms',
                    url="https://www.example.com/cpp-algorithms",
                    description="Learn how to code base algorithms in c++",
                    provider=md.Organization(name='Example University', url="www.example.com")
                ),
                md.Course(
                    name='C++ Data Structures',
                    url="https://www.example.com/cpp-data-structures",
                    description="Learn about core c++ data structures.",
                    provider=md.Organization(name='Example University', url="www.example.com")
                )
            ]
        )
        expected_dict = {
            '@context': 'https://schema.org/',
            '@type': 'Course',
            'name': 'Learn Advanced C++ Topics',
            'image': ['https://example.com/photos/1x1/photo.jpg',
                    'https://example.com/photos/4x3/photo.jpg',
                    'https://example.com/photos/16x9/photo.jpg'],
            'description': 'Improve your C++ skills by learning advanced topics.',
            'provider': {'@type': 'Organization',
                        'name': 'Example University',
                        'url': 'www.ewample.com'},
            'offers': {'@type': 'Offer',
                        'availability': 'https://schema.org/InStock',
                        'price': 10.99,
                        'priceCurrency': 'EUR',
                        'category': 'Paid'},
            'hasCourseInstance': [{'@type': 'CourseInstance',
                                    'location': 'Example University',
                                    'courseMode': 'Blended',
                                    'courseSchedule': {'@type': 'Schedule',
                                                    'repeatCount': 31,
                                                    'repeatFrequency': 'Daily',
                                                    'duration': 'PT3H',
                                                    'startDate': '2024-07-01',
                                                    'endDate': '2024-07-31'},
                                    'instructor': {'@type': 'Person',
                                                'name': 'Ira D.',
                                                'description': 'Professor at '
                                                                'X-University',
                                                'image': 'http://example.com/person.jpg'}},
                                {'@type': 'CourseInstance',
                                    'courseMode': 'Online',
                                    'courseWorkload': 'P2D'}],
            'hasPart': [{'@type': 'Course',
                        'name': 'C++ Algorithms',
                        'url': 'https://www.example.com/cpp-algorithms',
                        'description': 'Learn how to code base algorithms in c++',
                        'provider': {'@type': 'Organization',
                                    'name': 'Example University',
                                    'url': 'www.example.com'}},
                        {'@type': 'Course',
                        'name': 'C++ Data Structures',
                        'url': 'https://www.example.com/cpp-data-structures',
                        'description': 'Learn about core c++ data structures.',
                        'provider': {'@type': 'Organization',
                                    'name': 'Example University',
                                    'url': 'www.example.com'}}],
            'about': ['C++ Coding', 'Backend Engineering'],
            'aggregateRating': {'@type': 'AggregateRating',
                                'reviewCount': 450,
                                'ratingCount': 1234,
                                'ratingValue': 4,
                                'bestRating': 5.0,
                                'worstRating': 0.0},
            'availableLanguage': ['fr', 'es'],
            'coursePrerequisites': ['Basic understanding of C++ up to arrays and '
                                    'functions.',
                                    'https://www.example.com/beginnerCpp'],
            'datePublished': '2024-03-21',
            'educationalCredentialAwarded': {'@type': 'EducationalOccupationalCredential',
                                            'name': 'CourseProvider Certificate',
                                            'url': 'www.example.com',
                                            'credentialCategory': 'Certificate',
                                            'offers': {'@type': 'Offer',
                                                        'availability': 'https://schema.org/InStock',
                                                        'price': 5,
                                                        'priceCurrency': 'USD',
                                                        'category': 'Paid'}},
            'educationalLevel': 'Advanced',
            'financialAidEligible': 'Scholaship Available',
            'inLanguage': 'en',
            'publisher': {'@type': 'Organization',
                        'name': 'CourseWebsite',
                        'url': 'www.examplecoursewebsite.com'},
            'review': {'@type': 'Review',
                        'author': {'@type': 'Person', 'name': 'Lou S.'},
                        'reviewRating': {'@type': 'Rating',
                                        'ratingValue': 6,
                                        'bestRating': 10,
                                        'worstRating': 0.0},
                        'datePublished': '2024-08-31'},
            'syllabusSections': [{'@type': 'Syllabus',
                                'name': 'Memory Allocation',
                                'description': 'Learn how memory is allocated when '
                                                'creating C++ variables.',
                                'timeRequired': 'PT6H'},
                                {'@type': 'Syllabus',
                                'name': 'C++ Pointers',
                                'description': 'Learn what C++ pointer is and when they '
                                                'are used.',
                                'timeRequired': 'PT11H'}],
            'teaches': ['Practice and apply systems thinking to plan for change',
                        'Understand how memory allocation works.'],
            'totalHistoricalEnrollment': 12345,
            'video': {'@type': 'VideoObject',
                    'name': 'Video name',
                    'thumbnailUrl': 'www.example.com/thumbnailurl.jpg',
                    'uploadDate': '2024-03-28T08:00:00+08:00',
                    'contentUrl': 'www.example.com/mp4',
                    'description': 'A video previewing this course'}}
        generated_dict = course.to_dict()
        self.assertDictEqual(generated_dict, expected_dict, "Error in the expected breadcrumb_list dictionary")
        self.assertEqual(course._validate_gsc(generated_dict), True, "The required properties should be there")

    def test04_dataset(self):
        dataset = md.Dataset(
            description="Storm Data is provided by the National Weather Service (NWS) and contain statistics on...",
            name="NCDC Storm Events Database",
            distribution=[
                md.DataDownload(
                    encoding_format="CSV",
                    content_url="https://www.ncdc.noaa.gov/stormevents/ftp.jsp"
                ),
                md.DataDownload(
                    encoding_format="XML",
                    content_url="https://gis.ncdc.noaa.gov/all-records/catalog/search/resource/details.page?id=gov.noaa.ncdc:C00510"
                ),
            ],
            url="https://catalog.data.gov/dataset/ncdc-storm-events-database",
            sameAs="https://gis.ncdc.noaa.gov/geoportal/catalog/search/resource/details.page?id=gov.noaa.ncdc:C00510",
            identifier=[
                "https://doi.org/10.1000/182",
                "https://identifiers.org/ark:/12345/fk1234"
            ],
            keywords=[
                "ATMOSPHERE > ATMOSPHERIC PHENOMENA > CYCLONES",
                "ATMOSPHERE > ATMOSPHERIC PHENOMENA > DROUGHT",
                "ATMOSPHERE > ATMOSPHERIC PHENOMENA > FOG",
                "ATMOSPHERE > ATMOSPHERIC PHENOMENA > FREEZE"
            ],
            license="https://creativecommons.org/publicdomain/zero/1.0/",
            isAccessibleForFree=True,
            hasPart=[
                md.Dataset(
                    name="Sub dataset 01",
                    description="Informative description of the first subdataset...",
                    license="https://creativecommons.org/publicdomain/zero/1.0/",
                    creator=md.Organization(name="Sub dataset 01 creator")
                ),
                md.Dataset(
                    name="Sub dataset 02",
                    description="Informative description of the second subdataset...",
                    license="https://creativecommons.org/publicdomain/zero/1.0/",
                    creator=md.Organization(name="Sub dataset 02 creator")
                )
            ],
            creator=md.Organization(
                name="OC/NOAA/NESDIS/NCEI > National Centers for Environmental Information, NESDIS, NOAA, U.S. Department of Commerce",
                url="https://www.ncei.noaa.gov/",
                contactPoint=md.ContactPoint(
                    contactType="customer service",
                    telephone="+1-828-271-4800",
                    email="ncei.orders@noaa.gov"
                )
            ),
            funder=md.Organization(
                name="National Weather Service",
                sameAs="https://ror.org/00tgqzw13"
            ),
            includedInDataCatalog=md.DataCatalog(
                name="data.gov"
            ),
            temporal_coverage="1950-01-01/2013-12-18",
            spatial_coverage=md.Place(
                geo=md.GeoShape(
                    box="18.0 -65.0 72.0 172.0"
                )
            )
        )
        expected_dict = {
            '@context': 'https://schema.org/',
            '@type': 'Dataset',
            'name': 'NCDC Storm Events Database',
            'url': 'https://catalog.data.gov/dataset/ncdc-storm-events-database',
            'description': 'Storm Data is provided by the National Weather Service (NWS) '
                            'and contain statistics on...',
            'distribution': [{'@type': 'DataDownload',
                            'contentUrl': 'https://www.ncdc.noaa.gov/stormevents/ftp.jsp',
                            'encodingFormat': 'CSV'},
                            {'@type': 'DataDownload',
                            'contentUrl': 'https://gis.ncdc.noaa.gov/all-records/catalog/search/resource/details.page?id=gov.noaa.ncdc:C00510',
                            'encodingFormat': 'XML'}],
            'sameAs': 'https://gis.ncdc.noaa.gov/geoportal/catalog/search/resource/details.page?id=gov.noaa.ncdc:C00510',
            'identifier': ['https://doi.org/10.1000/182',
                            'https://identifiers.org/ark:/12345/fk1234'],
            'keywords': ['ATMOSPHERE > ATMOSPHERIC PHENOMENA > CYCLONES',
                        'ATMOSPHERE > ATMOSPHERIC PHENOMENA > DROUGHT',
                        'ATMOSPHERE > ATMOSPHERIC PHENOMENA > FOG',
                        'ATMOSPHERE > ATMOSPHERIC PHENOMENA > FREEZE'],
            'license': 'https://creativecommons.org/publicdomain/zero/1.0/',
            'isAccessibleForFree': True,
            'hasPart': [{'@type': 'Dataset',
                        'name': 'Sub dataset 01',
                        'description': 'Informative description of the first '
                                        'subdataset...',
                        'license': 'https://creativecommons.org/publicdomain/zero/1.0/',
                        'creator': {'@type': 'Organization',
                                    'name': 'Sub dataset 01 creator'}},
                        {'@type': 'Dataset',
                        'name': 'Sub dataset 02',
                        'description': 'Informative description of the second '
                                        'subdataset...',
                        'license': 'https://creativecommons.org/publicdomain/zero/1.0/',
                        'creator': {'@type': 'Organization',
                                    'name': 'Sub dataset 02 creator'}}],
            'creator': {'@type': 'Organization',
                        'name': 'OC/NOAA/NESDIS/NCEI > National Centers for Environmental '
                                'Information, NESDIS, NOAA, U.S. Department of Commerce',
                        'url': 'https://www.ncei.noaa.gov/',
                        'contactPoint': {'@type': 'ContactPoint',
                                        'contactType': 'customer service',
                                        'telephone': '+1-828-271-4800',
                                        'email': 'ncei.orders@noaa.gov'}},
            'funder': {'@type': 'Organization',
                        'name': 'National Weather Service',
                        'sameAs': 'https://ror.org/00tgqzw13'},
            'includedInDataCatalog': {'@type': 'DataCatalog', 'name': 'data.gov'},
            'temporalCoverage': '1950-01-01/2013-12-18',
            'spatialCoverage': {'@type': 'Place',
                                'geo': {'@type': 'GeoShape',
                                        'box': '18.0 -65.0 72.0 172.0'}}}
        generated_dict = dataset.to_dict()
        self.assertDictEqual(generated_dict, expected_dict, "Error in the expected dataset dictionary")
        self.assertEqual(dataset._validate_gsc(generated_dict), True, "The required properties should be there")

    def test05_carousel(self):
        movie1 = md.Movie(
            name="A star is born",
            url="https://example.com/2024-best-picture-noms#a-star-is-born",
            image="https://example.com/photos/6x9/photo.jpg",
            date_created="2024-10-05",
            director=md.Person(name="Bradley Cooper"),
            review=md.Review(
                author=md.Person(name="John D."),
                review_rating=md.Rating(rating_value=5)
            ),
            aggregate_rating=md.AggregateRating(
                rating_value=90,
                best_rating=100,
                rating_count=19141
            )
        )
        movie2 = md.Movie(
            name="Bohemian Rhapsody",
            url="https://example.com/2024-best-picture-noms#bohemian-rhapsody",
            image="https://example.com/photos/6x9/photo.jpg",
            date_created="2024-11-02",
            director=md.Person(name="Bryan Singer"),
            review=md.Review(
                author=md.Person(name="Vin S."),
                review_rating=md.Rating(rating_value=3)
            ),
            aggregate_rating=md.AggregateRating(
                rating_value=61,
                best_rating=100,
                rating_count=21985
            )
        )
        movie3 = md.Movie(
            name="Black Panther",
            url="https://example.com/2024-best-picture-noms#black-panther",
            image="https://example.com/photos/6x9/photo.jpg",
            date_created="2024-02-16",
            director=md.Person(name="Ryan Coogler"),
            review=md.Review(
                author=md.Person(name="Trevor R."),
                review_rating=md.Rating(rating_value=2)
            ),
            aggregate_rating=md.AggregateRating(
                rating_value=96,
                best_rating=100,
                rating_count=88211
            )
        )
        carousel = md.Carousel(items=[movie1, movie2, movie3])
        expected_dict = {
            '@context': 'https://schema.org/',
            '@type': 'ItemList',
            'itemListElement': [{'@type': 'ListItem',
                                'position': 1,
                                'item': {'@type': 'Movie',
                                        'name': 'A star is born',
                                        'image': 'https://example.com/photos/6x9/photo.jpg',
                                        'url': 'https://example.com/2024-best-picture-noms#a-star-is-born',
                                        'dateCreated': '2024-10-05',
                                        'director': {'@type': 'Person',
                                                        'name': 'Bradley Cooper'},
                                        'review': {'@type': 'Review',
                                                    'author': {'@type': 'Person',
                                                                'name': 'John D.'},
                                                    'reviewRating': {'@type': 'Rating',
                                                                    'ratingValue': 5,
                                                                    'bestRating': 5.0,
                                                                    'worstRating': 0.0}},
                                        'aggregateRating': {'@type': 'AggregateRating',
                                                            'ratingCount': 19141,
                                                            'ratingValue': 90,
                                                            'bestRating': 100,
                                                            'worstRating': 0.0}}},
                                {'@type': 'ListItem',
                                'position': 2,
                                'item': {'@type': 'Movie',
                                        'name': 'Bohemian Rhapsody',
                                        'image': 'https://example.com/photos/6x9/photo.jpg',
                                        'url': 'https://example.com/2024-best-picture-noms#bohemian-rhapsody',
                                        'dateCreated': '2024-11-02',
                                        'director': {'@type': 'Person',
                                                        'name': 'Bryan Singer'},
                                        'review': {'@type': 'Review',
                                                    'author': {'@type': 'Person',
                                                                'name': 'Vin S.'},
                                                    'reviewRating': {'@type': 'Rating',
                                                                    'ratingValue': 3,
                                                                    'bestRating': 5.0,
                                                                    'worstRating': 0.0}},
                                        'aggregateRating': {'@type': 'AggregateRating',
                                                            'ratingCount': 21985,
                                                            'ratingValue': 61,
                                                            'bestRating': 100,
                                                            'worstRating': 0.0}}},
                                {'@type': 'ListItem',
                                'position': 3,
                                'item': {'@type': 'Movie',
                                        'name': 'Black Panther',
                                        'image': 'https://example.com/photos/6x9/photo.jpg',
                                        'url': 'https://example.com/2024-best-picture-noms#black-panther',
                                        'dateCreated': '2024-02-16',
                                        'director': {'@type': 'Person',
                                                        'name': 'Ryan Coogler'},
                                        'review': {'@type': 'Review',
                                                    'author': {'@type': 'Person',
                                                                'name': 'Trevor R.'},
                                                    'reviewRating': {'@type': 'Rating',
                                                                    'ratingValue': 2,
                                                                    'bestRating': 5.0,
                                                                    'worstRating': 0.0}},
                                        'aggregateRating': {'@type': 'AggregateRating',
                                                            'ratingCount': 88211,
                                                            'ratingValue': 96,
                                                            'bestRating': 100,
                                                            'worstRating': 0.0}}}]}

        generated_dict = carousel.to_dict()
        self.assertDictEqual(generated_dict, expected_dict, "Error in the expected dataset dictionary")

    def test06_discussion_forum(self):
        discussion_forum = md.DiscussionForumPosting(
            author=md.Person(
                name="Katie Pope",
                url="https://example.com/user/katie-pope",
                agentInteractionStatistic=md.InteractionCounter(
                    interaction_type=md.WriteAction(),
                    user_interaction_count=8
                )
            ),
            date_published="2024-03-01T08:34:34+02:00",
            interaction_statistic=md.InteractionCounter(
                interaction_type=md.LikeAction(),
                user_interaction_count=27
            ),
            main_entity_of_page="https://example.com/post/very-popular-thread",
            headline="I went to the concert!",
            text="Look at how cool this concert was!",
            video=md.VideoObject(
                name="Video of concert",
                content_url="https://example.com/media/super-cool-concert.mp4",
                upload_date="2024-03-01T06:34:34+02:00",
                thumbnail_url="https://example.com/media/super-cool-concert-snap.jpg"
            ),
            url="https://example.com/post/very-popular-thread",
            comment=[
                md.Comment(
                    author=md.Person(
                        name="Saul Douglas",
                        url="https://example.com/user/saul-douglas",
                        agentInteractionStatistic=md.InteractionCounter(
                            interaction_type=md.WriteAction(),
                            user_interaction_count=167
                        )
                    ),
                    date_published="2024-03-01T09:46:02+02:00",
                    text="Who's the person you're with?"
                ),
                md.Comment(
                    author=md.Person(
                        name="Katie Pope",
                        url="https://example.com/user/katie-pope",
                        agentInteractionStatistic=md.InteractionCounter(
                            interaction_type=md.WriteAction(),
                            user_interaction_count=8
                        )
                    ),
                    date_published="2024-03-01T09:50:25+02:00",
                    text="That's my mom, isn't she cool?",
                    interaction_statistic=md.InteractionCounter(
                        interaction_type=md.LikeAction(),
                        user_interaction_count=7
                    )
                )
            ]
        )
        generated_dict = discussion_forum.to_dict()
        expected_dict = {
            '@context': 'https://schema.org/',
            '@type': 'DiscussionForumPosting',
            'url': 'https://example.com/post/very-popular-thread',
            'author': {'@type': 'Person',
                        'name': 'Katie Pope',
                        'url': 'https://example.com/user/katie-pope',
                        'agentInteractionStatistic': {'@type': 'InteractionCounter',
                                                    'userInteractionCount': 8,
                                                    'interactionType': {'@type': 'WriteAction'}}},
            'datePublished': '2024-03-01T08:34:34+02:00',
            'headline': 'I went to the concert!',
            'text': 'Look at how cool this concert was!',
            'video': {'@type': 'VideoObject',
                    'name': 'Video of concert',
                    'thumbnailUrl': 'https://example.com/media/super-cool-concert-snap.jpg',
                    'uploadDate': '2024-03-01T06:34:34+02:00',
                    'contentUrl': 'https://example.com/media/super-cool-concert.mp4'},
            'interactionStatistic': {'@type': 'InteractionCounter',
                                    'userInteractionCount': 27,
                                    'interactionType': {'@type': 'LikeAction'}},
            'mainEntityOfPage': 'https://example.com/post/very-popular-thread',
            'comment': [{'@type': 'Comment',
                        'author': {'@type': 'Person',
                                    'name': 'Saul Douglas',
                                    'url': 'https://example.com/user/saul-douglas',
                                    'agentInteractionStatistic': {'@type': 'InteractionCounter',
                                                                'userInteractionCount': 167,
                                                                'interactionType': {'@type': 'WriteAction'}}},
                        'datePublished': '2024-03-01T09:46:02+02:00',
                        'text': "Who's the person you're with?"},
                        {'@type': 'Comment',
                        'author': {'@type': 'Person',
                                    'name': 'Katie Pope',
                                    'url': 'https://example.com/user/katie-pope',
                                    'agentInteractionStatistic': {'@type': 'InteractionCounter',
                                                                'userInteractionCount': 8,
                                                                'interactionType': {'@type': 'WriteAction'}}},
                        'datePublished': '2024-03-01T09:50:25+02:00',
                        'text': "That's my mom, isn't she cool?",
                        'interactionStatistic': {'@type': 'InteractionCounter',
                                                'userInteractionCount': 7,
                                                'interactionType': {'@type': 'LikeAction'}}}]}
        self.assertDictEqual(generated_dict, expected_dict, "Error in the expected discussion forum dictionary")
        self.assertEqual(discussion_forum._validate_gsc(generated_dict), True, "The required properties should be there")

    def test07_education_qa(self):
        quiz = md.Quiz(
            has_part=[
                md.Question(
                    accepted_answer=md.Answer("receptor molecules"),
                    text="This is some fact about receptor molecules.",
                    edu_question_type="Flashcard"
                ),
                md.Question(
                    accepted_answer=md.Answer("cell membrane"),
                    text="This is some fact about the cell membrane.",
                    edu_question_type="Flashcard"
                ),
            ],
            about=md.Thing(name="Cell transport"),
            educational_alignment=md.AlignmentObject(
                alignment_type="educationalSubject",
                target_name="Biology"
            ))
        expected_dict = {
            '@context': 'https://schema.org/',
            '@type': 'Quiz',
            'hasPart': [{'@type': 'Question',
                        'text': 'This is some fact about receptor molecules.',
                        'acceptedAnswer': {'@type': 'Answer',
                                            'text': 'receptor molecules'},
                        'eduQuestionType': 'Flashcard'},
                        {'@type': 'Question',
                        'text': 'This is some fact about the cell membrane.',
                        'acceptedAnswer': {'@type': 'Answer', 'text': 'cell membrane'},
                        'eduQuestionType': 'Flashcard'}],
            'about': {'@type': 'Thing', 'name': 'Cell transport'},
            'educationalAlignment': {'@type': 'AlignmentObject',
                                    'alignmentType': 'educationalSubject',
                                    'targetName': 'Biology'}}
        generated_dict = quiz.to_dict()
        self.assertDictEqual(generated_dict, expected_dict, "Error in the expected quiz dictionary")
        self.assertEqual(quiz._validate_gsc(generated_dict), True, "The required properties should be there")

    def test08_employer_aggregate_rating(self):
        ear = md.EmployerAggregateRating(
            item_reviewed=md.Organization(
                name="World's Best Coffee Shop",
                same_as="https://example.com"
            ),
            rating_value=91,
            best_rating=100,
            worst_rating=1,
            rating_count=10561
        )
        generated_dict = ear.to_dict()
        expected_dict = {
            '@context': 'https://schema.org/',
            '@type': 'EmployerAggregateRating',
            'itemReviewed': {'@type': 'Organization',
                            'name': "World's Best Coffee Shop",
                            'sameAs': 'https://example.com'},
            'ratingCount': 10561,
            'ratingValue': 91,
            'bestRating': 100,
            'worstRating': 1
        }
        self.assertDictEqual(generated_dict, expected_dict, "Error in the expected employer aggregate rating dictionary")
        self.assertEqual(ear._validate_gsc(generated_dict), True, "The required properties should be there")

    def test09_estimated_salary(self):
        estimated_salary = md.Occupation(
            name="Software Developer, Applications",
            main_entity_of_page=md.WebPage(
                last_reviewed=md.Date("2024-07-23")
            ),
            description="Develops information systems by designing, developing, and installing software solutions",
            estimated_salary=md.MonetaryAmountDistribution(
                name="base",
                currency="USD",
                duration="P1Y",
                percentile10=100000.5,
                percentile25=115000,
                median=120000.28,
                percentile75=130000,
                percentile90=150000
            ),
            occupation_location=md.City(
                name="Mountain View"
            )
        )
        generated_dict = estimated_salary.to_dict()
        expected_dict = {
            '@context': 'https://schema.org/',
            '@type': 'Occupation',
            'estimatedSalary': {'@type': 'MonetaryAmountDistribution',
                                'name': 'base',
                                'currency': 'USD',
                                'duration': 'P1Y',
                                'percentile10': 100000.5,
                                'percentile25': 115000,
                                'median': 120000.28,
                                'percentile75': 130000,
                                'percentile90': 150000},
            'name': 'Software Developer, Applications',
            'occupationLocation': {'@type': 'City', 'name': 'Mountain View'},
            'description': 'Develops information systems by designing, developing, and '
                            'installing software solutions',
            'mainEntityOfPage': {'@type': 'WebPage', 'lastReviewed': '2024-07-23'}}
        self.assertDictEqual(generated_dict, expected_dict, "Error in the expected employer aggregate rating dictionary")
        self.assertEqual(estimated_salary._validate_gsc(generated_dict), True, "The required properties should be there")

    def test10_standard_event(self):
        event = md.Event(
            name="The Adventures of Kira and Morrison",
            start_date=md.DateTime("2025-07-21T19:00:00-05:00"),
            end_date=md.DateTime("2025-07-21T23:00:00-05:00"),
            event_attendance_mode=md.EventAttendanceModeEnumeration.Offline,
            event_status=md.EventStatusType.Scheduled,
            location=md.Place(
                name="Snickerpark Stadium",
                address=md.PostalAddress(
                    street_address="100 West Snickerpark Dr",
                    address_locality="Snickertown",
                    postal_code="19019",
                    address_region="PA",
                    address_country="US"
                )
            ),
            image=[
                "https://example.com/photos/1x1/photo.jpg",
                "https://example.com/photos/4x3/photo.jpg",
                "https://example.com/photos/16x9/photo.jpg"
            ],
            description="The Adventures of Kira and Morrison is coming to Snickertown in a can't miss performance.",
            offers=md.Offer(
                url="https://www.example.com/event_offer/12345_202403180430",
                price=30,
                price_currency="USD",
                availability=md.ItemAvailability.InStock,
                valid_from=md.DateTime("2024-05-21T12:00:00")
            ),
            performer=md.PerformingGroup(
                name="Kira and Morrison"
            ),
            organizer=md.Organization(
                name="Kira and Morrison Music",
                url="https://kiraandmorrisonmusic.com"
            )
        )
        generated_dict = event.to_dict()
        expected_dict = {
            '@context': 'https://schema.org/',
            '@type': 'Event',
            'name': 'The Adventures of Kira and Morrison',
            'location': {'@type': 'Place',
                        'name': 'Snickerpark Stadium',
                        'address': {'@type': 'PostalAddress',
                                    'addressCountry': 'US',
                                    'addressLocality': 'Snickertown',
                                    'addressRegion': 'PA',
                                    'postalCode': '19019',
                                    'streetAddress': '100 West Snickerpark Dr'}},
            'startDate': '2025-07-21T19:00:00-05:00',
            'description': 'The Adventures of Kira and Morrison is coming to Snickertown '
                            "in a can't miss performance.",
            'endDate': '2025-07-21T23:00:00-05:00',
            'eventAttendanceMode': 'https://schema.org/OfflineEventAttendanceMode',
            'eventStatus': 'https://schema.org/EventScheduled',
            'image': ['https://example.com/photos/1x1/photo.jpg',
                    'https://example.com/photos/4x3/photo.jpg',
                    'https://example.com/photos/16x9/photo.jpg'],
            'offers': {'@type': 'Offer',
                        'url': 'https://www.example.com/event_offer/12345_202403180430',
                        'availability': 'https://schema.org/InStock',
                        'price': 30,
                        'priceCurrency': 'USD',
                        'validFrom': '2024-05-21T12:00:00'},
            'organizer': {'@type': 'Organization',
                        'name': 'Kira and Morrison Music',
                        'url': 'https://kiraandmorrisonmusic.com'},
            'performer': {'@type': 'PerformingGroup', 'name': 'Kira and Morrison'}}
        self.assertDictEqual(generated_dict, expected_dict, "Error in the standard event dictionary")
        self.assertEqual(event._validate_gsc(generated_dict), True, "The required properties should be there")

    def test11_fact_check(self):
        fact_check = md.ClaimReview(
            url="https://example.com/news/science/worldisflat.html",
            claim_reviewed="The world is flat",
            item_reviewed=md.Claim(
                author=md.Organization(
                    name="Square World Society",
                    same_as="https://example.flatworlders.com/we-know-that-the-world-is-flat"
                ),
                date_published="2024-06-20T09:50:25+02:00",
                appearance=md.NewsArticle(
                    url="https://example.com/news/a122121",
                    headline="Square Earth - Flat earthers for the Internet age",
                    date_published="2024-06-22T09:50:25+02:00",
                    author=md.Person(name="T. Tellar", url="http://example.com/progile/t-tellar"),
                    image="https://example.com/photos/1x1/photo.jpg",
                    publisher=md.Organization(
                        name="Skeptical News",
                        logo=md.ImageObject(
                            url="https://example.com/logo.jpg"
                        )
                    )
                )
            ),
            author=md.Organization(
                name="Example.com science watch"
            ),
            review_rating=md.Rating(
                rating_value=1,
                best_rating=5,
                worst_rating=1,
                alternate_name="False"
            )
        )
        generated_dict = fact_check.to_dict()
        expected_dict = {
            '@context': 'https://schema.org/',
            '@type': 'ClaimReview',
            'url': 'https://example.com/news/science/worldisflat.html',
            'author': {'@type': 'Organization', 'name': 'Example.com science watch'},
            'reviewRating': {'@type': 'Rating',
                            'alternateName': 'False',
                            'ratingValue': 1,
                            'bestRating': 5,
                            'worstRating': 1},
            'itemReviewed': {'@type': 'Claim',
                            'author': {'@type': 'Organization',
                                        'name': 'Square World Society',
                                        'sameAs': 'https://example.flatworlders.com/we-know-that-the-world-is-flat'},
                            'datePublished': '2024-06-20T09:50:25+02:00',
                            'appearance': {'@type': 'NewsArticle',
                                            'image': 'https://example.com/photos/1x1/photo.jpg',
                                            'url': 'https://example.com/news/a122121',
                                            'author': {'@type': 'Person',
                                                        'name': 'T. Tellar',
                                                        'url': 'http://example.com/progile/t-tellar'},
                                            'datePublished': '2024-06-22T09:50:25+02:00',
                                            'headline': 'Square Earth - Flat earthers for '
                                                        'the Internet age',
                                            'publisher': {'@type': 'Organization',
                                                        'name': 'Skeptical News',
                                                        'logo': {'@type': 'ImageObject',
                                                                    'url': 'https://example.com/logo.jpg'}}}},
            'claimReviewed': 'The world is flat'}
        self.assertDictEqual(generated_dict, expected_dict, "Error in the expected fact check dictionary")
        self.assertEqual(fact_check._validate_gsc(generated_dict), True, "The required properties should be there")

    def test12_faq(self):
        faq = md.FAQPage(
            main_entity=[
                md.Question(
                    name="How to find an apprenticeship?",
                    accepted_answer=md.Answer(
                        text="<p>We provide an official service to search through available apprenticeships. To get started, create an account here, specify the desired region, and your preferences. You will be able to search through all officially registered open apprenticeships.</p>"
                    )
                ),
                md.Question(
                    name="Whom to contact?",
                    accepted_answer=md.Answer(
                        text="You can contact the apprenticeship office through our official phone hotline above, or with the web-form below. We generally respond to written requests within 7-10 days."
                    )
                )
            ]
        )
        expected_dict = {
            '@context': 'https://schema.org/',
            '@type': 'FAQPage',
            'mainEntity': [{'@type': 'Question',
                            'name': 'How to find an apprenticeship?',
                            'acceptedAnswer': {'@type': 'Answer',
                                                'text': '<p>We provide an official service '
                                                        'to search through available '
                                                        'apprenticeships. To get started, '
                                                        'create an account here, specify '
                                                        'the desired region, and your '
                                                        'preferences. You will be able to '
                                                        'search through all officially '
                                                        'registered open '
                                                        'apprenticeships.</p>'}},
                            {'@type': 'Question',
                            'name': 'Whom to contact?',
                            'acceptedAnswer': {'@type': 'Answer',
                                                'text': 'You can contact the '
                                                        'apprenticeship office through our '
                                                        'official phone hotline above, or '
                                                        'with the web-form below. We '
                                                        'generally respond to written '
                                                        'requests within 7-10 days.'}}]}
        generated_dict = faq.to_dict()
        self.assertDictEqual(generated_dict, expected_dict, "Error in the expected fact check dictionary")
        self.assertEqual(faq._validate_gsc(generated_dict), True, "The required properties should be there")

    def test14_learning_video(self):
        learning_video = md.LearningVideo(
            name="An introduction to Genetics",
            description="Explanation of the basics of Genetics for beginners.",
            learning_resource_type="Concept Overview",
            educational_level="High School (US)",
            content_url="https://www.example.com/video/123/file.mp4",
            thumbnail_url=[
                "https://example.com/photos/1x1/photo.jpg",
                "https://example.com/photos/4x3/photo.jpg",
                "https://example.com/photos/16x9/photo.jpg"
            ],
            upload_date="2024-03-31T08:00:00+08:00"
        )
        generated_dict = learning_video.to_dict()
        expected_dict = {
            '@context': 'https://schema.org/',
            '@type': ['VideoObject', 'LearningResource'],
            'name': 'An introduction to Genetics',
            'thumbnailUrl': ['https://example.com/photos/1x1/photo.jpg',
                            'https://example.com/photos/4x3/photo.jpg',
                            'https://example.com/photos/16x9/photo.jpg'],
            'uploadDate': '2024-03-31T08:00:00+08:00',
            'contentUrl': 'https://www.example.com/video/123/file.mp4',
            'description': 'Explanation of the basics of Genetics for beginners.',
            'educationalLevel': 'High School (US)',
            'learningResourceType': 'Concept Overview'}
        self.assertDictEqual(generated_dict, expected_dict, "Error in the expected learning video dictionary")
        self.assertEqual(learning_video._validate_gsc(generated_dict), True, "The required properties should be there")

        learning_video = md.LearningVideo(
            name="An introduction to XYZ",
            description="Solving equations using exponent properties",
            educational_level="High school (US)",
            educational_alignment=md.AlignmentObject(
                educational_framework="Common Core",
                target_name="HSA-SSE.B.3",
                target_url="https://www.corestandards.org/Math/Content/HSA/SSE/#CCSS.Math.Content.HSA.SSE.B.3"
            ),
            content_url="https://www.example.com/video/123/file.mp4",
            thumbnail_url=[
                "https://example.com/photos/1x1/photo.jpg",
                "https://example.com/photos/4x3/photo.jpg",
                "https://example.com/photos/16x9/photo.jpg"
            ],
            has_part=[
                md.LearningClip(
                    learning_resource_type="Concept Overview",
                    name="Understanding exponents",
                    start_offset=40,
                    end_offset=120,
                    url="https://www.example.com/example?t=501"
                ),
                md.LearningClip(
                    learning_resource_type="Problem Walkthrough",
                    name="Example problem 1: suspended wires",
                    start_offset=150,
                    end_offset=225,
                    text="Consider a weight suspended from two wires as shown in Figure. Find the tension in each wire.",
                    url="https://www.example.com/example?t=30"
                ),
                md.LearningClip(
                    learning_resource_type="Problem Walkthrough",
                    name="Example problem 2: exponents",
                    start_offset=275,
                    end_offset=500,
                    text="Consider a weight suspended from five wires as shown in Figure. Find the tension in one wire.",
                    url="https://www.example.com/example?t=201"
                )
            ],
            upload_date="2024-03-31T08:00:00+08:00"
        )
        generated_dict = learning_video.to_dict()
        expected_dict = {
            '@context': 'https://schema.org/',
            '@type': ['VideoObject', 'LearningResource'],
            'name': 'An introduction to XYZ',
            'thumbnailUrl': ['https://example.com/photos/1x1/photo.jpg',
                            'https://example.com/photos/4x3/photo.jpg',
                            'https://example.com/photos/16x9/photo.jpg'],
            'uploadDate': '2024-03-31T08:00:00+08:00',
            'contentUrl': 'https://www.example.com/video/123/file.mp4',
            'description': 'Solving equations using exponent properties',
            'hasPart': [{'@type': ['Clip', 'LearningResource'],
                        'name': 'Understanding exponents',
                        'url': 'https://www.example.com/example?t=501',
                        'startOffset': 40,
                        'endOffset': 120,
                        'learningResourceType': 'Concept Overview'},
                        {'@type': ['Clip', 'LearningResource'],
                        'name': 'Example problem 1: suspended wires',
                        'url': 'https://www.example.com/example?t=30',
                        'startOffset': 150,
                        'endOffset': 225,
                        'learningResourceType': 'Problem Walkthrough',
                        'text': 'Consider a weight suspended from two wires as shown in '
                                'Figure. Find the tension in each wire.'},
                        {'@type': ['Clip', 'LearningResource'],
                        'name': 'Example problem 2: exponents',
                        'url': 'https://www.example.com/example?t=201',
                        'startOffset': 275,
                        'endOffset': 500,
                        'learningResourceType': 'Problem Walkthrough',
                        'text': 'Consider a weight suspended from five wires as shown in '
                                'Figure. Find the tension in one wire.'}],
            'educationalAlignment': {'@type': 'AlignmentObject',
                                    'targetName': 'HSA-SSE.B.3',
                                    'educationalFramework': 'Common Core',
                                    'targetUrl': 'https://www.corestandards.org/Math/Content/HSA/SSE/#CCSS.Math.Content.HSA.SSE.B.3'},
            'educationalLevel': 'High school (US)'}
        self.assertDictEqual(generated_dict, expected_dict, "Error in the expected learning video dictionary")
        self.assertEqual(learning_video._validate_gsc(generated_dict), True, "The required properties should be there")

    def test15_math_solver(self):
        math_solver = md.LearningMathSolver(
            name="An awesome math solver",
            url="https://www.mathdomain.com/",
            usage_info="https://www.mathdomain.com/privacy",
            in_language="en",
            potential_action=md.SolveMathAction(
                target="https://mathdomain.com/solve?q={math_expression_string}",
                math_expression__input="required name=math_expression_string",
                edu_question_type=[
                    md.ProblemType.PolynomialEquation,
                    md.ProblemType.Derivative
                ]
            ),
            learning_resource_type="Math solver"
        )
        generated_dict = math_solver.to_dict()
        expected_dict = {
            '@context': 'https://schema.org/',
            '@type': ['MathSolver', 'LearningResource'],
            'name': 'An awesome math solver',
            'url': 'https://www.mathdomain.com/',
            'potentialAction': {'@type': 'SolveMathAction',
                                'eduQuestionType': ['Polynomial Equation', 'Derivative'],
                                'target': 'https://mathdomain.com/solve?q={math_expression_string}',
                                'mathExpression-input': 'required '
                                                        'name=math_expression_string'},
            'usageInfo': 'https://www.mathdomain.com/privacy',
            'inLanguage': 'en',
            'learningResourceType': 'Math solver'}
        self.assertDictEqual(generated_dict, expected_dict, "Error in the expected fact check dictionary")
        self.assertEqual(math_solver._validate_gsc(generated_dict), True, "The required properties should be there")


    def testZZ_broadcast_event(self):
        b1 = md.BroadcastEvent("First scheduled broadcast", "2018-10-27T14:00:00+00:00", '2018-10-27T14:37:14+00:00')
        b2 = md.BroadcastEvent("Second scheduled broadcast", "2018-10-27T18:00:00+00:00", '2018-10-27T18:37:14+00:00')
        potential_action = md.SeekToAction(
            target=md.URL("https://www.example.com/video/123/file.mp4?t={seek_to_second_number}")
        )
        v1 = md.VideoObject(
            name="Introducing the self-driving bicycle in the Netherlands",
            description="This spring, Google is introducing the self-driving bicycle in Amsterdam, the world's premier cycling city. The Dutch cycle more than any other nation in the world, almost 900 kilometres per year per person, amounting to over 15 billion kilometres annually. The self-driving bicycle enables safe navigation through the city for Amsterdam residents, and furthers Google's ambition to improve urban mobility with technology. Google Netherlands takes enormous pride in the fact that a Dutch team worked on this innovation that will have great impact in their home country.",
            thumbnail_url=[
                "https://example.com/photos/1x1/photo.jpg",
                "https://example.com/photos/4x3/photo.jpg",
                "https://example.com/photos/16x9/photo.jpg"
            ],
            upload_date="2024-03-31T08:00:00+08:00",
            duration="PT1M54S",
            content_url="https://www.example.com/video/123/file.mp4",
            embed_url="https://www.example.com/embed/123",
            interaction_statistic=md.InteractionCounter(5647018, md.WatchAction()),
            regions_allowed=['US', 'NL'],
            publication=[b1, b2],
            potential_action=potential_action
        )