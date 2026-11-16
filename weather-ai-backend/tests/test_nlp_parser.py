import unittest

from app.services.nlp_parser import parse_freeform_query


class NLPParserTests(unittest.TestCase):
    def test_strips_time_and_right_now_filler_from_location(self):
        parsed = parse_freeform_query(
            "what is the exact time and what is the weather in uppal rightnow"
        )

        self.assertEqual(parsed.location, "uppal")

    def test_strips_concatenated_right_now_from_location(self):
        parsed = parse_freeform_query(
            "what is the exact time and what is the weather in kakinadarightnow"
        )

        self.assertEqual(parsed.location, "kakinada")


if __name__ == "__main__":
    unittest.main()
