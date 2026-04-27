template_data = {
    "data": [
        {
            "name": "test_simple_text",
            "components": [
                {
                    "type": "BODY",
                    "text": "Hello, how are you? Thank you for reaching out to us."
                }
            ],
            "language": "en_US",
            "status": "APPROVED",
            "category": "MARKETING",
            "id": "972203162638803",
            'quality_score': {
                'score': 'UNKNOWN',
                'date': 1712830463,
            },
        },
        {
            "name": "test_dynamic_header_with_dynamic_body",
            "components": [
                {
                    "type": "HEADER",
                    "format": "TEXT",
                    "text": "Hello {{1}}",
                    "example": {
                        "header_text": [
                            "Nishant"
                        ]
                    }
                },
                {
                    "type": "BODY",
                    "text": "Greetings of the day! I hope you are safe and doing well. \n This is {{1}} from Odoo. My mobile number is {{2}}.\nI will be happy to help you with any queries you may have.\nThank you",
                    "example": {
                        "body_text": [
                            [
                                "Jigar",
                                "+91 12345 12345"
                            ]
                        ]
                    }
                }
            ],
            "language": "en_US",
            "status": "APPROVED",
            "category": "MARKETING",
            "id": "778510144283702",
            'quality_score': {
                'score': 'UNKNOWN',
                'date': 1712830464,
            },
        },
        {
            "name": "test_location_header",
            "components": [
                {
                    "type": "HEADER",
                    "format": "LOCATION"
                },
                {
                    "type": "BODY",
                    "text": "This is location header"
                }
            ],
            "language": "en_US",
            "status": "APPROVED",
            "category": "UTILITY",
            "id": "948089559317319",
            'quality_score': {
                'score': 'UNKNOWN',
                'date': 1712830465,
            },
        },
        {
            "name": "test_image_header",
            "components": [
                {
                    "type": "HEADER",
                    "format": "IMAGE",
                    "example": {
                        "header_handle": ["demo_image_url"]
                    }
                },
                {
                    "type": "BODY",
                    "text": "This is Image header"
                }
            ],
            "language": "en_US",
            "status": "APPROVED",
            "category": "UTILITY",
            "id": "948089559314656",
            'quality_score': {
                'score': 'GREEN',
                'date': 1712830466,
            },
        },
        {
            "name": "test_dynamic_header_body_button",
            "components": [
                {
                    "type": "HEADER",
                    "format": "TEXT",
                    "text": "Hello {{1}}",
                    "example": {
                        "header_text": [
                            "Nishant"
                        ]
                    }
                },
                {
                    "type": "BODY",
                    "text": "Greetings of the day! I hope you are safe and doing well. \n This is {{1}} from Odoo. My mobile number is {{2}}.\nI will be happy to help you with any queries you may have.\nThank you",
                    "example": {
                        "body_text": [
                            [
                                "Jigar",
                                "+91 12345 12345"
                            ]
                        ]
                    }
                },
                {
                    "type": "BUTTONS",
                    "buttons": [
                        {
                            "type": "URL",
                            "text": "Visit Website",
                            "url": "https://www.example.com/",
                            "example": [
                                "https://www.example.com/demo"
                            ]
                        }
                    ]
                }
            ],
            "language": "en_US",
            "status": "APPROVED",
            "category": "MARKETING",
            "id": "605909939256361",
            'quality_score': {
                'score': 'YELLOW',
                'date': 1712830467,
            },
        },
        {
            "name": "test_red_quality",
            "components": [
                {
                    "type": "BODY",
                    "text": "Hello, This is a red quality template.",
                }
            ],
            "language": "en_US",
            "status": "APPROVED",
            "category": "MARKETING",
            "id": "948089551314656",
            'quality_score': {
                'score': 'RED',
                'date': 1712830468,
            },
        }
    ]
}
