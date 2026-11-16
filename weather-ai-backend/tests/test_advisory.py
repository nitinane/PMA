import unittest

from app.services.advisory import generate_travel_advisory


class AdvisoryTests(unittest.TestCase):
    def test_generates_guidance_without_external_provider(self):
        result = generate_travel_advisory(
            "Uppal, Hyderabad",
            {
                "current_temp_c": 26.6,
                "current_humidity_pct": 36,
                "current_wind_kmh": 8.8,
                "daily": [
                    {
                        "temp_min_c": 20.1,
                        "temp_max_c": 29.4,
                        "precipitation_mm": 0,
                        "uv_index_max": 7,
                        "wind_max_kmh": 18,
                    }
                ],
            },
        )

        self.assertIn("UV levels reach 7", result)


if __name__ == "__main__":
    unittest.main()
