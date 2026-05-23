{
    "name": "Solar AI",
    "version": "19.0.1.0.0",
    "summary": "AI-first document processing and project orchestration for solar projects",
    "category": "Project",
    "depends": [
        "solar_project",
        "base_setup",
    ],
    "external_dependencies": {"python": ["httpx"]},
    "data": [
        "data/config_params.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
