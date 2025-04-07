from __future__ import annotations
from .core.object_type import CreativeWork, MediaObject, URL


class DataCatalog(CreativeWork):
    __description__ = """
        A collection of datasets.
    """
    __schema_properties__ = CreativeWork.__schema_properties__ | {
        "dataset": ['r', "Dataset"],
        "measurementMethod": ['r', "DefinedTerm", "Text", "URL", "MeasurementMethodEnum"],
        "measurementTechnique": ['r', "DefinedTerm", "Text", "URL", "MeasurementMethodEnum"],
    }

    def __init__(self, name: str, **kwargs) -> None:
        super().__init__(name=name, **kwargs)


class DataDownload(MediaObject):
    __description__ = """
        All or part of a Dataset in downloadable form.
    """
    __schema_properties__ = MediaObject.__schema_properties__ | {
        "measurementMethod": ['r', "DefinedTerm", "Text", "URL", "MeasurementMethodEnum"],
        "measurementTechnique": ['r', "DefinedTerm", "Text", "URL", "MeasurementMethodEnum"],
    }

    def __init__(self,
                 content_url: URL | str,
                 encoding_format: str | None = None,
                 **kwargs) -> None:
        super().__init__(content_url=content_url, encoding_format=encoding_format, **kwargs)


class Dataset(CreativeWork):
    __description__ = """
        A body of structured information describing some topic(s) of interest.
    """
    __schema_properties__ = CreativeWork.__schema_properties__ | {
        "distribution": ['r', "DataDownload"],
        "includedInDataCatalog": ['r', "DataCatalog"],
        "issn": ['r', "Text"],
        "measurementMethod": ['r', "DefinedTerm", "Text", "URL", "MeasurementMethodEnum"],
        "measurementTechnique": ['r', "DefinedTerm", "Text", "URL", "MeasurementMethodEnum"],
        "variableMeasured": ['r', "Property", "PropertyValue", "StatisticalVariable", "Text"]
    }
    __gsc_required_properties__ = [
        'description',
        'name',
        'distribution.contentUrl'
    ]

    def __init__(self,
                 name: str,
                 description: str,
                 distribution: DataDownload | list[DataDownload] | None = None,
                 **kwargs) -> None:
        super().__init__(description=description, name=name, distribution=distribution, **kwargs)
