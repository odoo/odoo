import unittest

from odoo.libs.documents.cues import (
    Cue,
    cues_as_text,
    format_offset,
    parse_offset,
    parse_srt,
    parse_vtt,
    render_srt,
    render_vtt,
)
from odoo.libs.documents.document import Document
from odoo.libs.documents.formats import (
    RECORDING_MIMETYPES,
    extension_for,
    get_format,
    mimetype_for,
)
from odoo.libs.documents.readers import CUES, TEXT, get_readers
from odoo.libs.documents.writers import get_writers

VTT = """WEBVTT

NOTE recorded by the meeting bridge

1
00:00:00.000 --> 00:00:02.500
<v Alice>Good morning

2
00:00:02.500 --> 00:00:06.250 align:start
Morning. Did the <b>invoice</b> go out?
"""

SRT = """1
00:00:00,000 --> 00:00:02,500
Alice: Good morning

2
00:00:02,500 --> 00:00:06,250
Morning. Did the invoice go out?
"""


class TestParsing(unittest.TestCase):
    def test_vtt_carries_timing_speaker_and_plain_text(self):
        cues = parse_vtt(VTT)
        self.assertEqual(len(cues), 2)
        self.assertEqual(cues[0], Cue(0.0, 2.5, "Good morning", "Alice"))
        self.assertEqual(cues[1].start, 2.5)
        self.assertEqual(cues[1].end, 6.25)
        self.assertEqual(cues[1].text, "Morning. Did the invoice go out?")
        self.assertEqual(cues[1].speaker, "")

    def test_a_note_block_is_not_a_cue(self):
        self.assertTrue(all("recorded by" not in cue.text for cue in parse_vtt(VTT)))

    def test_srt_reads_the_comma_separator(self):
        cues = parse_srt(SRT)
        self.assertEqual(len(cues), 2)
        self.assertEqual(cues[0].start, 0.0)
        self.assertEqual(cues[0].end, 2.5)

    def test_an_hourless_stamp_is_minutes_and_seconds(self):
        (cue,) = parse_vtt("WEBVTT\n\n01:30.500 --> 02:00.000\nlate\n")
        self.assertEqual(cue.start, 90.5)
        self.assertEqual(cue.end, 120.0)

    def test_a_cue_with_no_words_is_dropped(self):
        empty = "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\n<i></i>\n"
        self.assertEqual(parse_vtt(empty), [])

    def test_crlf_is_read(self):
        self.assertEqual(len(parse_vtt(VTT.replace("\n", "\r\n"))), 2)

    def test_character_references_are_decoded(self):
        track = "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nTom &amp; Jerry &lt;3\n"
        (cue,) = parse_vtt(track)
        self.assertEqual(cue.text, "Tom & Jerry <3")

    def test_a_reference_in_a_speaker_name_is_decoded_too(self):
        track = "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\n<v Ben &amp; Co>hi\n"
        (cue,) = parse_vtt(track)
        self.assertEqual(cue.speaker, "Ben & Co")

    def test_a_reference_that_spells_a_tag_is_not_read_as_one(self):
        track = "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\n&lt;b&gt;not bold&lt;/b&gt;\n"
        (cue,) = parse_vtt(track)
        self.assertEqual(cue.text, "<b>not bold</b>")

    def test_a_reference_is_decoded_once(self):
        track = "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nliteral &amp;lt; entity\n"
        (cue,) = parse_vtt(track)
        self.assertEqual(cue.text, "literal &lt; entity")

    def test_escaped_text_round_trips(self):
        cues = [Cue(0.0, 1.0, "literal &lt; entity & <tag>")]
        self.assertEqual(parse_vtt(render_vtt(cues)), cues)

    def test_an_invalid_code_point_stays_as_written_and_the_rest_reads(self):
        track = (
            "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nbad &#99999999; &#xD800; ok"
            "\n\n00:00:01.000 --> 00:00:02.000\n&#X41;&#66;\n"
        )
        self.assertEqual(
            [cue.text for cue in parse_vtt(track)],
            ["bad &#99999999; &#xD800; ok", "AB"],
        )

    def test_text_carrying_no_cue_reads_as_no_cues(self):
        self.assertEqual(parse_vtt("WEBVTT\n\nnothing here at all\n"), [])


class TestWriting(unittest.TestCase):
    def test_vtt_round_trips(self):
        cues = parse_vtt(VTT)
        self.assertEqual(parse_vtt(render_vtt(cues)), cues)

    def test_srt_round_trips(self):
        cues = parse_srt(SRT)
        self.assertEqual(parse_srt(render_srt(cues)), cues)

    def test_a_blank_line_inside_a_cue_survives_the_round_trip(self):
        cues = [Cue(0.0, 1.0, "para one\n\npara two")]
        self.assertEqual(parse_vtt(render_vtt(cues))[0].text.count("para"), 2)

    def test_vtt_states_its_header(self):
        self.assertTrue(render_vtt([Cue(0.0, 1.0, "hi")]).startswith("WEBVTT\n\n"))

    def test_srt_numbers_its_blocks_from_one(self):
        written = render_srt([Cue(0.0, 1.0, "a"), Cue(1.0, 2.0, "b")])
        self.assertEqual(written.splitlines()[0], "1")
        self.assertIn("2\n00:00:01,000 --> 00:00:02,000", written)

    def test_a_speaker_is_a_voice_tag_in_vtt_and_a_prefix_in_srt(self):
        cue = Cue(0.0, 1.0, "hello", "Alice")
        self.assertIn("<v Alice>hello", render_vtt([cue]))
        self.assertIn("Alice: hello", render_srt([cue]))

    def test_a_stamp_past_an_hour_keeps_its_hours(self):
        self.assertIn("01:00:00.000", render_vtt([Cue(3600.0, 3601.0, "x")]))

    def test_cues_as_text_is_the_words_alone(self):
        self.assertEqual(
            cues_as_text(parse_vtt(VTT)),
            "Good morning\nMorning. Did the invoice go out?",
        )

    def test_cues_as_text_can_say_who_spoke(self):
        self.assertEqual(
            cues_as_text(parse_vtt(VTT), speakers=True),
            "Alice: Good morning\nMorning. Did the invoice go out?",
        )

    def test_a_cue_is_sure_of_nothing_until_told(self):
        self.assertEqual(Cue(0.0, 1.0, "x").confidence, 0.0)
        self.assertEqual(Cue(0.0, 1.0, "x", "A", 0.92).confidence, 0.92)

    def test_an_offset_reads_as_minutes_until_it_needs_hours(self):
        self.assertEqual(format_offset(0), "00:00")
        self.assertEqual(format_offset(75.9), "01:15")
        self.assertEqual(format_offset(3725), "1:02:05")
        self.assertEqual(format_offset(-3), "00:00")

    def test_a_stamp_reads_back_as_the_offset_it_shows(self):
        for seconds in (0, 75, 3725):
            with self.subTest(seconds=seconds):
                self.assertEqual(parse_offset(format_offset(seconds)), seconds)
        self.assertEqual(parse_offset("[03:12]"), 192.0)
        self.assertEqual(parse_offset(12.5), 12.5)

    def test_a_stamp_that_is_not_one_reads_as_nothing(self):
        for stamp in (None, "", "soon", "1:2:3:4", "01:75", "-1:00", True):
            with self.subTest(stamp=stamp):
                self.assertIsNone(parse_offset(stamp))


class TestDocument(unittest.TestCase):
    def test_a_vtt_document_provides_cues(self):
        document = Document(VTT.encode(), "text/vtt", "meeting.vtt")
        self.assertTrue(document.provides(CUES))
        self.assertEqual(len(document.cues), 2)

    def test_a_vtt_document_reads_as_who_said_what(self):
        document = Document(VTT.encode(), "text/vtt", "meeting.vtt")
        self.assertEqual(
            document.text, "Alice: Good morning\nMorning. Did the invoice go out?"
        )
        self.assertNotIn("00:00:00.000", document.text)

    def test_an_srt_document_reads_the_same_way(self):
        document = Document(SRT.encode(), "application/x-subrip", "film.srt")
        self.assertEqual(len(document.cues), 2)
        self.assertTrue(document.text.startswith("Alice: Good morning"))

    def test_a_document_is_written_from_cues(self):
        cues = [Cue(0.0, 1.5, "spoken words")]
        document = Document.of(cues=cues, name="note")
        self.assertEqual(document.mimetype, "text/vtt")
        self.assertIn(b"WEBVTT", document.data)
        self.assertEqual(document.cues, cues)

    def test_cues_are_written_as_subrip_when_asked(self):
        document = Document.of(
            cues=[Cue(0.0, 1.0, "x")], mimetype="application/x-subrip"
        )
        self.assertTrue(document.data.startswith(b"1\n00:00:00,000"))

    def test_a_document_written_from_cues_still_reads_as_text(self):
        document = Document.of(cues=[Cue(0.0, 1.0, "spoken words")])
        self.assertEqual(document.text, "spoken words")


class TestRegistry(unittest.TestCase):
    def test_cues_is_a_representation_readers_and_writers_can_name(self):
        self.assertTrue(get_readers("text/vtt", CUES))
        self.assertTrue(get_writers("text/vtt", CUES))

    def test_the_text_of_a_cue_track_comes_from_a_reader_not_from_decoding(self):
        readers = get_readers("text/vtt", TEXT)
        self.assertEqual([reader.name for reader in readers], ["cued_text"])

    def test_a_recording_reads_as_text_through_its_cues(self):
        for mimetype in ("audio/mpeg", "audio/webm", "video/mp4"):
            with self.subTest(mimetype=mimetype):
                readers = get_readers(mimetype, TEXT)
                self.assertEqual([reader.name for reader in readers], ["cued_text"])

    def test_a_recording_with_no_transcriber_reads_as_nothing(self):
        document = Document(b"ID3\x04\x00fake", "audio/mpeg", "call.mp3")
        self.assertEqual(document.text, "")

    def test_recordings_are_formats_whose_representation_is_cues(self):
        self.assertIn("audio/mpeg", RECORDING_MIMETYPES)
        self.assertIn("audio/x-m4a", RECORDING_MIMETYPES)
        self.assertIn("video/webm", RECORDING_MIMETYPES)
        self.assertNotIn("text/vtt", RECORDING_MIMETYPES)
        ogg = get_format("audio/ogg")
        assert ogg is not None
        self.assertEqual(ogg.representation, CUES)

    def test_both_cue_formats_are_registered(self):
        vtt = get_format("text/vtt")
        assert vtt is not None
        self.assertEqual(vtt.representation, CUES)
        self.assertEqual(mimetype_for("srt"), "application/x-subrip")
        self.assertEqual(extension_for("text/vtt"), "vtt")

    def test_a_misdeclared_subrip_alias_still_resolves(self):
        srt = get_format("text/srt")
        assert srt is not None
        self.assertEqual(srt.extension, "srt")
