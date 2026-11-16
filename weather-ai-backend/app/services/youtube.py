from urllib.parse import quote_plus


async def fetch_location_youtube_videos(
    location_name: str, country: str | None = None, max_results: int = 3
) -> list[dict[str, str]]:
    """
    Generates curated YouTube search result URLs for the chosen location.
    """
    base_location = f"{location_name} {country or ''}".strip()

    search_queries = [
        {
            "title": f"{location_name} Travel Guide",
            "query": f"{base_location} travel guide",
        },
        {
            "title": f"{location_name} Travel Vlog & Tour",
            "query": f"{base_location} travel vlog tour",
        },
        {
            "title": f"Top Things to Do in {location_name}",
            "query": f"things to do in {base_location}",
        },
    ]

    results: list[dict[str, str]] = []
    for item in search_queries[:max_results]:
        encoded_query = quote_plus(item["query"])
        results.append(
            {
                "video_id": "",
                "title": item["title"],
                "channel": "YouTube Search",
                "url": f"https://www.youtube.com/results?search_query={encoded_query}",
                "thumbnail": "",
            }
        )

    return results