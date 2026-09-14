from odoo.tests.common import TransactionCase, tagged

from odoo.addons.gateway_ml.tools.ai_clients.deepgram import DeepgramClient


class _Client(DeepgramClient):
    def __init__(self):
        pass


CASES = {
    "alternatives": (
        {"alternatives": 3},
        {"alternatives": 3, "punctuate": "true"},
    ),
    "detect_language": (
        {"detect_language": True},
        {"detect_language": "true", "punctuate": "true"},
    ),
    "detect_topics_alias": (
        {"detect_topics": True},
        {"punctuate": "true", "topics": "true"},
    ),
    "diarize_plain": (
        {"diarize": True},
        {"diarize": "true", "punctuate": "true"},
    ),
    "diarize_versioned": (
        {"diarize": True, "diarize_version": "2023-01-01"},
        {"diarize": "true", "diarize_version": "2023-01-01", "punctuate": "true"},
    ),
    "empty": (
        {},
        {"punctuate": "true"},
    ),
    "entities_sentiment_intents": (
        {"detect_entities": True, "intents": True, "sentiment": True},
        {
            "detect_entities": "true",
            "intents": "true",
            "punctuate": "true",
            "sentiment": "true",
        },
    ),
    "keyterm_ignored_on_nova2": (
        {"keyterm": ["a"], "model": "nova-2"},
        {"model": "nova-2", "punctuate": "true"},
    ),
    "keyterm_on_flux": (
        {"keyterm": ["x"], "model": "flux-1"},
        {"keyterm": ["x"], "model": "flux-1", "punctuate": "true"},
    ),
    "keyterm_on_nova3_list": (
        {"keyterm": ["a", "b"], "model": "nova-3"},
        {"keyterm": ["a", "b"], "model": "nova-3", "punctuate": "true"},
    ),
    "keyterm_on_nova3_str": (
        {"keyterm": "solo", "model": "nova-3"},
        {"keyterm": ["solo"], "model": "nova-3", "punctuate": "true"},
    ),
    "keywords_ignored_on_nova3": (
        {"keywords": ["k"], "model": "nova-3"},
        {"model": "nova-3", "punctuate": "true"},
    ),
    "keywords_on_nova2_str": (
        {"keywords": "solo", "model": "nova-2"},
        {"keywords": ["solo"], "model": "nova-2", "punctuate": "true"},
    ),
    "keywords_on_nova2": (
        {"keywords": ["k1", "k2"], "model": "nova-2"},
        {"keywords": ["k1", "k2"], "model": "nova-2", "punctuate": "true"},
    ),
    "kitchen_sink": (
        {
            "alternatives": 2,
            "detect_entities": True,
            "detect_language": True,
            "diarize": True,
            "diarize_version": "v9",
            "filler_words": True,
            "intents": True,
            "keyterm": ["kt"],
            "language": "en",
            "model": "nova-3",
            "multichannel": True,
            "numerals": True,
            "paragraphs": True,
            "profanity_filter": True,
            "punctuate": True,
            "redact": ["r"],
            "replace": ["p"],
            "search": ["s"],
            "sentiment": True,
            "smart_format": True,
            "summarize": "v2",
            "timestamps": True,
            "topics": True,
            "utterances": True,
        },
        {
            "alternatives": 2,
            "detect_entities": "true",
            "detect_language": "true",
            "diarize": "true",
            "diarize_version": "v9",
            "filler_words": "true",
            "intents": "true",
            "keyterm": ["kt"],
            "language": "en",
            "model": "nova-3",
            "multichannel": "true",
            "numerals": "true",
            "paragraphs": "true",
            "profanity_filter": "true",
            "punctuate": "true",
            "redact": ["r"],
            "replace": ["p"],
            "search": ["s"],
            "sentiment": "true",
            "smart_format": "true",
            "summarize": "v2",
            "timestamps": "true",
            "topics": "true",
            "utterances": "true",
        },
    ),
    "model_language": (
        {"language": "es", "model": "nova-3"},
        {"language": "es", "model": "nova-3", "punctuate": "true"},
    ),
    "paragraphs_utterances": (
        {"paragraphs": True, "utterances": True},
        {"paragraphs": "true", "punctuate": "true", "utterances": "true"},
    ),
    "profanity_numerals_multichannel": (
        {"multichannel": True, "numerals": True, "profanity_filter": True},
        {
            "multichannel": "true",
            "numerals": "true",
            "profanity_filter": "true",
            "punctuate": "true",
        },
    ),
    "punctuate_default_on": (
        {"model": "nova-2"},
        {"model": "nova-2", "punctuate": "true"},
    ),
    "punctuate_off": (
        {"punctuate": False},
        {},
    ),
    "redact_replace": (
        {"redact": ["pci"], "replace": ["a:b"]},
        {"punctuate": "true", "redact": ["pci"], "replace": ["a:b"]},
    ),
    "search_list": (
        {"search": ["foo", "bar"]},
        {"punctuate": "true", "search": ["foo", "bar"]},
    ),
    "search_not_list": (
        {"search": "foo"},
        {"punctuate": "true"},
    ),
    "smart_format_filler": (
        {"filler_words": True, "smart_format": True},
        {"filler_words": "true", "punctuate": "true", "smart_format": "true"},
    ),
    "summarize_bogus": (
        {"summarize": "nonsense"},
        {"punctuate": "true", "summarize": "true"},
    ),
    "summarize_false": (
        {"summarize": False},
        {"punctuate": "true"},
    ),
    "summarize_str_true": (
        {"summarize": "true"},
        {"punctuate": "true", "summarize": "true"},
    ),
    "summarize_true": (
        {"summarize": True},
        {"punctuate": "true", "summarize": "true"},
    ),
    "summarize_v2": (
        {"summarize": "v2"},
        {"punctuate": "true", "summarize": "v2"},
    ),
    "timestamps_false": (
        {"timestamps": False},
        {"punctuate": "true", "timestamps": "false"},
    ),
    "timestamps_true": (
        {"timestamps": True},
        {"punctuate": "true", "timestamps": "true"},
    ),
    "topics": (
        {"topics": True},
        {"punctuate": "true", "topics": "true"},
    ),
}


@tagged("post_install", "-at_install", "gateway_ml")
class TestDeepgramTranscriptionParams(TransactionCase):
    def test_captured_cases_are_unchanged(self):
        client = _Client()
        for name, (kwargs, expected) in CASES.items():
            with self.subTest(case=name):
                self.assertEqual(
                    client._prepare_transcription_params(**kwargs), expected
                )
