from __future__ import annotations
from datetime import datetime, date, time, timedelta
from enum import Enum
import json
import re
from .data_type import URL, DateTime, Date, Time, DataType, Boolean
from typing import Any


class Thing:
    """Base class for all Schema.org entities."""
    __description__ = "The most generic type of item."
    __schema_properties__ = {
        "name": "Text",
        "description": "Text",
        "image": ['r', "ImageObject", "URL", "Text"],
        "url": ['r', "URL", "Text"],
        "additionalType": ["Text", "URL"],
        "alternateName": "Text",
        "disambiguatingDescription": "Text",
        "identifier": ['r', "PropertyValue", "Text", "URL"],
        "mainEntityOfPage": ["CreativeWork", "URL"],
        "SeekToAction": ["Action"],
        "sameAs": "URL",
        "subjectOf": ['r', "CreativeWork", "Event"],
        "potentialAction": "Action"
    }
    __type_name__ = None
    __context_url__ = None
    __gsc_required_properties__ = []

    def __init__(self, **extra_properties) -> None:
        self.type_name = self.__type_name__ or self.__class__.__name__
        self.context_url = self.__context_url__ or "https://schema.org/"
        self.extra_properties = self._validate_and_store_extra_properties(extra_properties)

    def set_property(self, property_key, property_value) -> None:
        self.extra_properties[property_key] = property_value
        self.extra_properties = self._validate_and_store_extra_properties(self.extra_properties)

    @staticmethod
    def snake_to_camel(snake_str: str) -> str:
        """
        Convert a snake_case string to camelCase.

        Args:
            snake_str (str): The input string in snake_case.

        Returns:
            str: The converted string in camelCase.
        """
        parts = snake_str.split("_")
        return parts[0] + "".join(word.capitalize() for word in parts[1:])

    def _validate_and_store_extra_properties(self, properties: dict) -> dict:
        """Validate and store extra Schema.org properties.

        Args:
            properties (dict): Additional Schema.org properties.

        Returns:
            dict: Validated properties.

        Raises:
            ValueError: If a property is not recognized.
            TypeError: If a property has an incorrect type.
        """
        validated = {}

        for key, values in properties.items():
            self.__dict__[key] = values
            annotation = None
            if '__' in key:
                key, annotation = key.split('__')
            key = self.snake_to_camel(key)
            if key not in self.__schema_properties__:
                raise ValueError(f"'{key}' is not a recognized property for {self.type_name}")
            if annotation:
                key = f"{key}-{annotation}"
                validated[key] = values
                continue
            expected_types = self.__schema_properties__[key]
            expected_types = expected_types if isinstance(expected_types, list) else [expected_types]

            is_repeatable = 'r' in expected_types
            expected_types = [t for t in expected_types if t != 'r']  # Remove 'r' flag

            if not isinstance(values, list):
                values = [values]  # Ensure values is always a list

            if len(values) > 1 and not is_repeatable:
                raise TypeError(f"'{key}' is not repeatable but multiple values were provided")

            validated[key] = [
                self._validate_value_type(key, value, expected_types)
                for value in values if value not in (None, "")
            ]

            if len(validated[key]) == 0:
                validated.pop(key)
            elif not is_repeatable or len(validated[key]) == 1:
                validated[key] = validated[key][0]

        return validated

    def _validate_value_type(self, key: str, value, expected_types: list):
        """
        Validate and convert a value based on expected types.
        Returns:
            Any value

        Raises:
            TypeError: If a property has an incorrect type.
        """
        if value is None:
            return None
        if isinstance(value, Enum) and 'Text' in expected_types:
            return value.value
        if isinstance(value, str) and {'Text', 'CssSelectorType', 'PronounceableText', 'URL', 'XpathType'} & set(expected_types):
            return value
        if isinstance(value, int) and 'Integer' in expected_types:
            return value
        if isinstance(value, bool) and 'Boolean' in expected_types:
            return value
        if isinstance(value, (float, int)) and 'Number' in expected_types:
            return value
        hierarchy = []
        for cls in value.__class__.mro():
            hierarchy.append(cls.__name__)
            if cls in (Thing, DataType):
                break
        if any(item in hierarchy for item in expected_types):
            return value
        if hasattr(value, 'enum_class') and (
            value.enum_class.__name__ in expected_types or
            'Text' in expected_types
        ):
            return value

        # Date, DateTime, and Time conversions
        date_type_map = {
            'Date': (date, Date),
            'DateTime': (datetime, DateTime),
            'Time': (time, Time),
            'Duration': (str, str)
        }

        for type_name, (native_type, schema_type) in date_type_map.items():
            if type_name in expected_types:
                if isinstance(value, native_type):
                    return schema_type(value)  # Convert native type to schema type
                if isinstance(value, str):  # Try parsing if it's a string
                    try:
                        return schema_type(native_type.fromisoformat(value))
                    except ValueError:
                        pass  # Fall through to error handling

        raise TypeError(
            f"Invalid type for '{key}'. Expected one of {expected_types}."
        )

    def _convert_value(self, value: Any, include_context: bool) -> Any:
        """Convert nested `Thing` instances to dictionaries.

        Args:
            value (Any): The value to be converted.

        Returns:
            Any: JSON-LD compatible representation.
        """
        if isinstance(value, Thing):  # If the value is a subclass of Thing, call to_dict()
            if hasattr(value, "value"):
                return value.value
            return value.to_dict(include_context=include_context)
        if isinstance(value, (DataType, Enum)):
            return value.value
        if isinstance(value, list):  # Recursively handle lists of Things
            return [self._convert_value(v, include_context=False) for v in value]
        return value

    def super_paths(self) -> str:
        """
        Get the inheritance path of the current class.

        Returns:
            str: The class hierarchy formatted as "Thing > Parent > Child".
        """
        hierarchy = []
        for cls in self.__class__.mro():  # Get method resolution order
            hierarchy.append(cls.__name__)
            if cls is Thing:  # Stop at Thing
                break
        return " > ".join(reversed(hierarchy))

    def get_property(self, path: str, from_dict: dict, default=None):
        keys = path.split(".")
        value = from_dict

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            elif isinstance(value, list):  # Handle list of dictionaries
                value = [item.get(key, default) if isinstance(item, dict) else default for item in value]
            else:
                return default  # Property not found

        return value

    def to_dict(self, include_context=True) -> dict:
        """
            Generate a JSON-LD representation of the object.
            Returns:
                dict
        """
        if include_context:
            data = {
                "@context": self.context_url,
                "@type": self.type_name,
            }
        else:
            data = {
                "@type": self.type_name,
            }

        # Convert and add extra properties
        for key, value in self.extra_properties.items():
            data[key] = self._convert_value(value, include_context=False)

        return data

    def _validate_gsc(self, data):
        errors = []
        not_required_anymore = []  # TODO  # noqa: F841
        for required_prop in self.__gsc_required_properties__:
            if isinstance(required_prop, tuple):
                prop, condition = required_prop
                if condition == "unless_last_element":
                    value = self.get_property(prop, data)
                    if not isinstance(value, list):
                        value = [value]
                    value = value[:-1]
                elif condition == "or":
                    valid = False
                    for p in prop:
                        values = self.get_property(p, data)
                        if values:
                            valid = True
                    if not valid:
                        if not any(values):
                            errors.append(
                                f"One of {', '.join(prop)} is required for Google Search Console in {self.type_name}"
                            )
                    continue
                else:
                    raise ValueError(f"Unknown condition '{condition}' in GSC validation.")
            else:
                prop = required_prop
                value = self.get_property(prop, data)
            if not isinstance(value, list):
                value = [value]
            if None in value:
                errors.append(f"{prop} is required for Google Search Console for the feature {self.type_name}")
        return True if len(errors) == 0 else errors

    def to_json_ld_script(self) -> str:
        """
        Generate a JSON-LD <script> tag representation.
        Returns:
            str
        """
        json_ld_data = self.to_dict()
        return f'<script type="application/ld+json">{json.dumps(json_ld_data, indent=2)}</script>'


class Intangible(Thing):
    __description__ = "A utility class that serves as the umbrella for a number of 'intangible' things such as quantities, structured values, etc."


class AlignmentObject(Intangible):
    __description__ = """
        An intangible item that describes an alignment between a learning resource and a node in an educational framework.
    """
    __schema_properties__ = Intangible.__schema_properties__ | {
        "alignmentType": "Text",
        "educationalFramework": "Text",
        "targetDescription": "Text",
        "targetName": "Text",
        "targetUrl": "URL"
    }

    def __init__(self,
                 alignment_type: str | None = None,
                 target_name: str | None = None,
                 **kwargs) -> None:
        super().__init__(alignment_type=alignment_type, target_name=target_name, **kwargs)


class StructuredValue(Intangible):
    __description__ = """
        Structured values are used when the value of a property has a more
        complex structure than simply being a textual value or a reference
        to another thing.
    """


class PropertyValue(StructuredValue):
    __description__ = """
        A property-value pair, e.g. representing a feature of a product or
        place. Use the 'name' property for the name of the property. If there is
        an additional human-readable version of the value, put that into the
        'description' property.

        Always use specific schema.org properties when a) they exist and b) you
        can populate them. Using PropertyValue as a substitute will typically
        not trigger the same effect as using the original, specific property.
    """
    __schema_properties__ = StructuredValue.__schema_properties__ | {
        "maxValue": "Number",
        "measurementMethod": ['r', "DefinedTerm", "MeasurementMethodEnum", "Text", "URL"],
        "measurementTechnique": ['r', "DefinedTerm", "MeasurementMethodEnum", "Text", "URL"],
        "minValue": "Number",
        "propertyID": ['r', "Text", "URL"],
        "unitCode": ["Text", "URL"],
        "unitText": ["Text"],
        "value": ["Boolean", "Text", "Number", "StructuredValue"],
        "valueReference": ["DefinedTerm", "Text", "MeasurementTypeEnumeration", "PropertyValue", "QualitativeValue", "QuantitativeValue", "StructuredValue"]
    }

    def __init__(self,
                 name: str | None = None,
                 value: Boolean | float | StructuredValue | str | None = None,
                 **kwargs):
        super().__init__(name=name, value=value, **kwargs)


class QuantitativeValue(StructuredValue):
    __description__ = """
        A point value or interval for product characteristics and other purposes.
    """
    __schema_properties__ = StructuredValue.__schema_properties__ | {
        "additionalProperty": ['r', "PropertyValue"],
        "maxValue": "Number",
        "minValue": "Number",
        "unitCode": ["Text", "URL"],
        "unitText": "Text",
        "value": ["Boolean", "Number", "StructuredValue", "Text"],
        "valueReference": ["DefinedTerm", "Text", "MeasurementTypeEnumeration", "PropertyValue", "QualitativeValue", "QuantitativeValue", "StructuredValue"]
    }

    def __init__(self,
                 value: Boolean | float | StructuredValue | str,
                 unit_text: str | None = None,
                 **kwargs) -> None:
        super().__init__(value=value, unit_text=unit_text, **kwargs)


class QuantitativeValueDistribution(StructuredValue):
    __description__ = "A statistical distribution of values."
    __schema_properties__ = StructuredValue.__schema_properties__ | {
        "duration": "Duration",
        "median": "Number",
        "percentile10": "Number",
        "percentile25": "Number",
        "percentile75": "Number",
        "percentile90": "Number"
    }


class MonetaryAmountDistribution(QuantitativeValueDistribution):
    __description__ = "A statistical distribution of monetary amounts."
    __schema_properties__ = QuantitativeValueDistribution.__schema_properties__ | {
        "currency": "Text"
    }


class MonetaryAmount(StructuredValue):
    __description__ = """
        A monetary value or range. This type can be used to describe an amount
        of money such as $50 USD, or a range as in describing a bank account
        being suitable for a balance between £1,000 and £1,000,000 GBP, or the
        value of a salary, etc. It is recommended to use PriceSpecification
        Types to describe the price of an Offer, Invoice, etc.
    """
    __schema_properties__ = StructuredValue.__schema_properties__ | {
        "currency": "Text",
        "maxValue": "Number",
        "minValue": "Number",
        "validFrom": ["Date", "DateTime"],
        "validThrough": ["Date", "DateTime"],
        "value": ["Boolean", "Number", "StructuredValue", "Text"]
    }

    def __init__(self,
                 value: Boolean | float | StructuredValue | str,
                 currency: str,
                 **kwargs) -> None:
        super().__init__(value=value, currency=currency, **kwargs)


class GeoShape(StructuredValue):
    __description__ = "The geographic shape of a place. A GeoShape can be described using several properties whose values are based on latitude/longitude pairs. Either whitespace or commas can be used to separate latitude and longitude; whitespace should be used when writing a list of several such points."
    __schema_properties__ = Intangible.__schema_properties__ | {
        "address": ['PostalAddress', "Text"],
        "addressCountry": ["Country", "Text"],
        "box": ["Text"],
        "circle": ["Text"],
        "elevation": ["Number", "Text"],
        "line": "Text",
        "polygon": "Text",
        "postalCode": "Text"
    }


class ContactPoint(StructuredValue):
    __description__ = "A contact point—for example, a Customer Complaints department."
    __schema_properties__ = StructuredValue.__schema_properties__ | {
        "areaServed": ['r', "AdministrativeArea", "GeoShape", "Place", "Text"],
        "availableLanguage": ['r', "Language", "Text"],
        "contactOption": ['r', "ContactPointOption"],
        "contactType": "Text",
        "email": "Text",
        "faxNumber": ['r', "Text"],
        "hoursAvailable": ["OpeningHoursSpecification"],
        "productSupported": ['r', "Product", "Text"],
        "telephone": ['r', "Text"],
    }


class Person(Thing):
    """Represents a Person entity based on Schema.org."""
    __description__ = "A person (alive, dead, undead, or fictional)."
    __schema_properties__ = Thing.__schema_properties__ | {
        "additionalName": ['r', "Text"],
        "address": ["PostalAddress", "Text"],
        "affiliation": ['r', "Organization"],
        "agentInteractionStatistic": "InteractionCounter",
        "alumniOf": ['r', "EducationalOrganization", "Organization"],
        "award": ['r', "Text"],
        "birthDate": "Date",
        "birthPlace": "Place",
        "brand": ['r', "Brand", "Organization"],
        "callSign": ['r', "Text"],
        "children": ['r', "Person"],
        "colleague": ['r', "Person", "URL"],
        "contactPoint": ['r', "ContactPoint"],
        "deathDate": "Date",
        "deathPlace": "Place",
        "duns": "Text",
        "email": ['r', "Text"],
        "familyName": "Text",
        "faxNumber": ['r', "Text"],
        "follows": ['r', "Person"],
        "funder": ['r', "Person", "Organization"],
        "funding": ['r', "Grant"],
        "gender": ["GenderType", "Text"],
        "givenName": "Text",
        "globalLocationNumber": "Text",
        "hasCertification": ['r', "Certification"],
        "hasCredential": ['r', "EducationalOccupationalCredential"],
        "hasOccupation": ['r', "Occupation"],
        "hasOfferCatalog": ['r', "OfferCatalog"],
        "hasPOS": ['r', "Place"],
        "height": ["Distance", "QuantitativeValue"],
        "homeLocation": ["ContactPoint", "Place"],
        "honorificPrefix": "Text",
        "honorificSuffix": "Text",
        "interactionStatistic": "InteractionCounter",
        "isicV4": "Text",
        "jobTitle": ['r', "DefinedTerm", "Text"],
        "knows": ['r', "Person"],
        "knowsAbout": ['r', "Thing", "Text", "URL"],
        "knowsLanguage": ['r', "Language", "Text"],
        "makesOffer": ['r', "Offer"],
        "memberOf": ['r', "MemberProgramTier", "Organization", "ProgramMebership"],
        "naics": "Text",
        "nationality": ['r', "Country"],
        "netWorth": ["MonetaryAmount", "PriceSpecification"],
        "owns": ['r', "OwnershipInfo", "Product"],
        "parent": ['r', "Person"],
        "performerIn": ['r', "Event"],
        "publishingPrinciples": ['r', "CreativeWork", "URL"],
        "relatedTo": ['r', "Person"],
        "seeks": ['r', "Demand"],
        "sibling": ['r', "Person"],
        "skills": ['r', "DefinedTerm", "Text"],
        "sponsor": ['r', "Organization", "Person"],
        "spouse": "Person",
        "taxID": "Text",
        "telephone": ['r', "Text"],
        "vatID": 'Text',
        "weight": "QuantitativeValue",
        "workLocation": ['r', "ContactPoint", "Place"],
        "worksFor": ['r', "Organization"]
    }

    def __init__(self,
                 name: str,
                 url: URL | str | None = None,
                 description: str | None = None,
                 image: ImageObject | URL | str | list[ImageObject | URL | str] | None = None,
                 **kwargs) -> None:

        super().__init__(name=name, url=url, description=description, image=image, **kwargs)


class Organization(Thing):
    """Represents an Organization entity based on Schema.org."""
    __description__ = "An organization such as a school, NGO, corporation, club, etc."
    __schema_properties__ = Thing.__schema_properties__ | {
        "acceptedPaymentMethod": ['r', "LoanOrCredit", "PaymentMethod", "Text"],
        "actionableFeedbackPolicy": ['r', "CreativeWork", "URL"],
        "address": ["PostalAddress", "Text"],
        "agentInteractionStatistic": "InteractionCounter",
        "aggregateRating": "AggregateRating",
        "alumni": ['r', "Person"],
        "areaServed": ['r', "AdministrativeArea", "GeoShape", "Place", "Text"],
        "award": ['r', "Text"],
        "brand": ['r', "Brand", "Organization"],
        "contactPoint": ['r', "ContactPoint"],
        "correctionsPolicy": ['r', "CreativeWork", "URL"],
        "department": ['r', "Organization"],
        "dissolutionDate": "Date",
        "diversityPolicy": ['r', "CreativeWork", "URL"],
        "diversityStaffingReport": ['r', "Article", "URL"],
        "duns": "Text",
        "email": ['r', "Text"],
        "employee": ['r', "Person"],
        "ethicsPolicy": ['r', "CreativeWork", "URL"],
        "event": ['r', "Event"],
        "faxNumber": ['r', "Text"],
        "founder": ['r', "Person"],
        "foundingDate": "Date",
        "foundingLocation": "Place",
        "funder": ['r', "Organization", "Person"],
        "globalLocationNumber": "Text",
        "hasCredential": ['r', "EducationalOccupationalCredential"],
        "hasMerchantReturnPolicy": ['r', "MerchantReturnPolicy"],
        "hasOfferCatalog": ['r', "OfferCatalog"],
        "hasPOS": ['r', "Place"],
        "isicV4": "Text",
        "keywords": ['r', "DefinedTerm", "Text", "URL"],
        "knowsAbout": ['r', "Text", "URL", "Thing"],
        "knowsLanguage": ['r', "Text", "Language"],
        "legalName": "Text",
        "leiCode": "Text",
        "location": ['r', "Place", "PostalAddress", "Text", "VirtualLocation"],
        "logo": ["ImageObject", "URL"],
        "makesOffer": ['r', "Offer"],
        "member": ['r', "Organization", "Person"],
        "memberOf": ['r', "Organization", "ProgramMembership"],
        "naics": "Text",
        "numberOfEmployees": "QuantitativeValue",
        "ownershipFundingInfo": ['r', "CreativeWork", "Text", "URL"],
        "owns": ['r', "OwnershipInfo", "Product"],
        "parentOrganization": "Organization",
        "publishingPrinciples": ['r', "CreativeWork", "URL"],
        "review": ['r', "Review"],
        "seeks": ['r', "Demand"],
        "slogan": "Text",
        "sponsor": ['r', "Organization", "Person"],
        "subOrganization": ['r', "Organization"],
        "taxID": "Text",
        "telephone": ['r', "Text"],
        "unnamedSourcesPolicy": ['r', "CreativeWork", "URL"],
        "vatID": "Text"
    }

    def __init__(self,
                 name: str,
                 url: URL | str | None = None,
                 description: str | None = None,
                 image: ImageObject | URL | str | list[ImageObject | URL | str] | None = None,
                 **kwargs
        ) -> None:

        super().__init__(name=name, url=url, description=description, image=image, **kwargs)


class PerformingGroup(Organization):
    __description__ = """
        A performance group, such as a band, an orchestra, or a circus.
    """


class CreativeWork(Thing):
    __description__ = """
        The most generic kind of creative work, including books, movies,
        photographs, software programs, etc.
    """
    __schema_properties__ = Thing.__schema_properties__ | {
        "about": ['r', "Thing", "Text"],
        "abstract": "Text",
        "accessMode": ['r', "Text"],
        "accessModeSufficient": ['r', "Text"],
        "accessibilityAPI": ['r', "Text"],
        "accessibilityControl": ['r', "Text"],
        "accessibilityFeature": ['r', "Text"],
        "accessibilityHazard": ['r', "Text"],
        "accessibilitySummary": "Text",
        "accountablePerson": "Person",
        "aggregateRating": "AggregateRating",
        "alternativeHeadline": "Text",
        "archivedAt": ['r', "WebPage", "URL"],
        "assesses": ['r', "DefinedTerm", "Text"],
        "associatedMedia": ['r', "MediaObject"],
        "audience": ['r', "Audience"],
        "audio": ['r', "AudioObject", "Clip"],
        "author": ['r', "Organization", "Person"],
        "award": ['r', "Text"],
        "character": ['r', "Person"],
        "citation": ['r', "CreativeWork", "Text"],
        "comment": ['r', "Comment"],
        "commentCount": "Integer",
        "conditionsOfAccess": "Text",
        "contentLocation": "Place",
        "contentRating": ['r', "Text", "Rating"],
        "contentReferenceTime": "DateTime",
        "contributor": ['r', "Organization", "Person"],
        "copyrightHolder": ['r', "Organization", "Person"],
        "copyrightNotice": "Text",
        "copyrightYear": "Number",
        "correction": ['r', "CreativeWork", "Text"],
        "countryOfOrigin": "Country",
        "creativeWorkStatus": ['r', "DefinedTerm", "Text"],
        "creator": ['r', "Organization", "Person"],
        "creditText": "Text",
        "dateCreated": ["Date", "DateTime"],
        "dateModified": ["Date", "DateTime"],
        "datePublished": ["Date", "DateTime"],
        "discussionUrl": "URL",
        "editor": ['r', "Person"],
        "educationalAlignment": ['r', "AlignmentObject"],
        "educationalLevel": ['r', "EducationalLevel", "DefinedTerm", "Text"],
        "educationalUse": ['r', "DefinedTerm", "Text"],
        "encoding": ['r', "MediaObject"],
        "exampleOfWork": ['r', "CreativeWork"],
        "expires": "Date",
        "funder": ['r', "Organization", "Person"],
        "genre": ['r', "Text", "URL"],
        "hasPart": ['r', "CreativeWork"],
        "headline": "Text",
        "inLanguage": ['r', "Language", "Text"],
        "interactionStatistic": ['r', "InteractionCounter"],
        "interactivityType": "Text",
        "isAccessibleForFree": "Boolean",
        "isBasedOn": ['r', "CreativeWork", "Product", "URL"],
        "isFamilyFriendly": "Boolean",
        "isPartOf": ['r', "CreativeWork"],
        "keywords": ['r', "DefinedTerm", "Text", "URL"],
        "learningResourceType": ['r', "DefinedTerm", "Text"],
        "license": ['r', "CreativeWork", "URL"],
        "locationCreated": "Place",
        "mainEntity": ['r', "Thing"],
        "mainEntityOfPage": ['r', "CreativeWork", "URL"],
        "material": ['r', "Product", "Text", "URL"],
        "mentions": ['r', "Thing"],
        "offers": ['r', "Offer"],
        "pattern": ['r', "DefinedTerm", "Text"],
        "position": ["Integer", "Text"],
        "producer": ['r', "Organization", "Person"],
        "provider": ['r', "Organization", "Person"],
        "publication": ['r', "PublicationEvent"],
        "publisher": ['r', "Organization", "Person"],
        "publisherImprint": "Organization",
        "publishingPrinciples": ['r', "CreativeWork", "URL"],
        "recordedAt": ['r', "Event"],
        "releasedEvent": ['r', "PublicationEvent"],
        "review": ['r', "Review"],
        "schemaVersion": ['r', "Text", "URL"],
        "sdDatePublished": "Date",
        "sdLicense": ['r', "CreativeWork", "URL"],
        "sdPublisher": ['r', "Organization", "Person", "URL"],
        "sourceOrganization": "Organization",
        "spatialCoverage": "Place",
        "sponsor": ['r', "Organization", "Person"],
        "teaches": ['r', "DefinedTerm", "Text"],
        "temporalCoverage": ['r', "DateTime", "Text", "URL"],
        "text": "Text",
        "thumbnailUrl": ['r', "URL"],
        "timeRequired": "Duration",
        "translationOfWork": "CreativeWork",
        "translator": ['r', "Organization", "Person"],
        "typicalAgeRange": "Text",
        "usageInfo": ['r', "CreativeWork", "URL"],
        "version": ["Number", "Text"],
        "video": ['r', "Clip", "VideoObject"],
        "workExample": ['r', "CreativeWork"],
        "workTranslation": "CreativeWork"
    }

    def __init__(self,
                 name: str | None = None,
                 image: ImageObject | URL | list[ImageObject | URL] | None = None,
                 url: URL | None = None,
                 **kwargs):
        super().__init__(name=name, image=image, url=url, **kwargs)


class WebPage(CreativeWork):
    __description__ = """
        A web page. Every web page is implicitly assumed to be declared to be of
        type WebPage, so the various properties about that webpage, such as
        breadcrumb may be used. We recommend explicit declaration if these
        properties are specified, but if they are found outside of an itemscope,
        they will be assumed to be about the page.
    """
    __schema_properties__ = CreativeWork.__schema_properties__ | {
        "breadcrumb": ["BreadcrumbList", "Text"],
        "lastReviewed": "Date",
        "mainContentOfPage": "WebPageElement",
        "primaryImageOfPage": "ImageObject",
        "relatedLink": ['r', "URL"],
        "reviewedBy": ['r', "Organization", "Person"],
        "significantLink": ['r', "URL"],
        "speakable": ['r', "SpeakableSpecification", "URL"],
        "specialty": ['r', "Specialty"]
    }


class MediaObject(CreativeWork):
    __description__ = """
        A media object, such as an image, video, audio, or text object embedded in a web page or a downloadable dataset i.e. DataDownload. Note that a creative work may have many media objects associated with it on the same web page. For example, a page about a single song (MusicRecording) may have a music video (VideoObject), and a high and low bandwidth audio stream (2 AudioObject's).
    """
    __schema_properties__ = CreativeWork.__schema_properties__ | {
        "associatedArticle": ['r', "NewsArticle"],
        "bitrate": "Text",
        "contentSize": "Text",
        "contentUrl": "URL",
        "duration": "Duration",
        "embedUrl": "URL",
        "encodesCreativeWork": "CreativeWork",
        "encodingFormat": ['r', "Text", "URL"],
        "endTime": ["DateTime", "Time"],
        "height": ["Distance", "QuantitativeValue"],
        "ineligibleRegion": ['r', "GeoShape", "Place", "Text"],
        "interpretedAsClaim": ['r', "Claim"],
        "playerType": ['r', "Text"],
        "productionCompany": ['r', "Organization"],
        "regionsAllowed": ['r', "Place", "Text"],
        "requiresSubscription": ["Boolean", "MediaSubscription"],
        "sha256": "Text",
        "startTime": ["DateTime", "Time"],
        "uploadDate": ["Date", "DateTime"],
        "width": ["Distance", "QuantitativeValue"]
    }

    def __init__(self,
                 name: str | None = None,
                 image: ImageObject | URL | list[ImageObject | URL] | None = None,
                 url: URL | None = None,
                 **kwargs) -> None:
        super().__init__(name=name, image=image, url=url, **kwargs)


class ImageObject(MediaObject):
    __description__ = "An image file."
    __schema_properties__ = MediaObject.__schema_properties__ | {
        "caption": ["MediaObject", "Text"],
        "embeddedTextCaption": "Text",
        "exifData": ["PropertyValue", "Text"],
        "representativeOfPage": "Boolean"
    }

    def __init__(self,
                 name: str | None = None,
                 url: URL | str | None = None,
                 **kwargs) -> None:
        super().__init__(name, url=url, **kwargs)


class ListItem(Intangible):
    __description__ = """
        An list item, e.g. a step in a checklist or how-to description.
    """
    __schema_properties__ = Intangible.__schema_properties__ | {
        "item": ["Thing", "URL", "Text"],
        "nextItem": "ListItem",
        "position": ["Integer", "Text"],
        "previousItem": "ListItem"
    }

    def __init__(self,
                 name: str | None = None,
                 position: int | None = None,
                 item: URL | str | None = None,
                 **kwargs) -> None:
        super().__init__(name=name, position=position, item=item, **kwargs)


class ItemList(Intangible):
    __description__ = """
        A list of items of any sort—for example, Top 10 Movies About Weathermen, or Top 100 Party Songs. Not to be confused with HTML lists, which are often used only for formatting.
    """
    __schema_properties__ = Intangible.__schema_properties__ | {
        "itemListElement": ['r', "ListItem", "Text", "Thing"],
        "itemListOrder": ["ItemListOrderType", "Text"],
        "numberOfItems": ["Integer"]
    }

    def __init__(self,
                 item_list_element: list[ListItem | Thing],
                 item_list_order: str | None = None,
                 number_of_items: int | None = None, **kwargs):
        super().__init__(
            item_list_element=item_list_element,
            item_list_order=item_list_order,
            number_of_items=number_of_items,
            **kwargs
        )
        if item_list_order not in ['Ascending', 'Descending', 'Unordered', None]:
            raise ValueError("Bad item list order")


class PostalAddress(ContactPoint):
    __description__ = "The mailing address."
    __schema_properties__ = ContactPoint.__schema_properties__ | {
        "addressCountry": ["Country", "Text"],
        "addressLocality": "Text",
        "addressRegion": "Text",
        "postOfficeBoxNumber": "Text",
        "postalCode": "Text",
        "streetAddress": "Text"
    }

    def __init__(self,
                 address_country: str | None = None,
                 address_locality: str | None = None,
                 address_region: str | None = None,
                 post_office_box_number: str | None = None,
                 postal_code: str | None = None,
                 street_address: str | None = None,
                 **kwargs) -> None:
        super().__init__(
            address_country=address_country,
            address_locality=address_locality,
            address_region=address_region,
            post_office_box_number=post_office_box_number,
            postal_code=postal_code,
            street_address=street_address,
            **kwargs
        )


class Place(Thing):
    __description__ = "Entities that have a somewhat fixed, physical extension."
    __schema_properties__ = Thing.__schema_properties__ | {
        "additionalProperty": ['r', "PropertyValue"],
        "address": ["PostalAddress", "Text"],
        "aggregateRating": "AggregateRating",
        "amenityFeature": ['r', "LocationFeatureSpecification"],
        "branchCode": "Text",
        "containedInPlace": "Place",
        "containsPlace": ["r", "Place"],
        "event": ['r', "Event"],
        "faxNumber": ['r', "Text"],
        "geo": ["GeoCoordinates", "GeoShape"],
        "geoContains": ["GeospatialGeometry", "Place"],
        "geoCoveredBy": ["GeospatialGeometry", "Place"],
        "geoCovers": ["GeospatialGeometry", "Place"],
        "geoCrosses": ["GeospatialGeometry", "Place"],
        "geoDisjoint": ["GeospatialGeometry", "Place"],
        "geoEquals": ["GeospatialGeometry", "Place"],
        "geoIntersects": ["GeospatialGeometry", "Place"],
        "geoOverlaps": ["GeospatialGeometry", "Place"],
        "geoTouches": ["GeospatialGeometry", "Place"],
        "geoWithin": ["GeospatialGeometry", "Place"],
        "globalLocationNumber": "Text",
        "hasCertification": ['r', "Certification"],
        "hasDriveThroughService": "Boolean",
        "hasGS1DigitalLink": ['r', "URL"],
        "hasMap": ['r', "Map", "URL"],
        "isAccessibleForFree": "Boolean",
        "isicV4": "Text",
        "keywords": ['r', "DefinedTerm", "Text", "URL"],
        "latitude": ["Number", "Text"],
        "logo": ["ImageObject", "URL"],
        "longitude": ["Number", "Text"],
        "maximumAttendeeCapacity": "Integer",
        "openingHoursSpecification": "OpeningHoursSpecification",
        "photo": ['r', "ImageObject", "Photograph"],
        "publicAccess": "Boolean",
        "review": ['r', "Review"],
        "slogan": "Text",
        "smokingAllowed": "Boolean",
        "specialOpeningHoursSpecification": "OpeningHoursSpecification",
        "telephone": ['r', "Text"],
        "tourBookingPage": ['r', "URL"]
    }

    def __init__(self,
                 name: str | None = None,
                 address: PostalAddress | str | None = None,
                 **kwargs) -> None:
        super().__init__(name=name, address=address, **kwargs)


class AdministrativeArea(Place):
    __description__ = """
        A geographical region, typically under the jurisdiction of a particular
        government.
    """


class City(AdministrativeArea):
    __description__ = "A city or town."


class Country(AdministrativeArea):
    __description__ = "A country"


class State(AdministrativeArea):
    __description__ = "A state or province of a country"


class VirtualLocation(Intangible):
    __description__ = """
        An online or virtual location for attending events. For example, one may
        attend an online seminar or educational event. While a virtual location
        may be used as the location of an event, virtual locations should not be
        confused with physical locations in the real world.
    """

    def __init__(self, url: URL | str, **kwargs) -> None:
        super().__init__(url=url, **kwargs)


class ItemAvailability(Enum):
    InStock = "https://schema.org/InStock"
    SoldOut = "https://schema.org/SoldOut"
    PreOrder = "https://schema.org/PreOrder"


class OfferCategory(Enum):
    Free = "Free"
    PartiallyFree = "Partially Free"
    Subscription = "Subscription"
    Paid = "Paid"


class Offer(Intangible):
    __description__ = """
        An offer to transfer some rights to an item or to provide a service —
        for example, an offer to sell tickets to an event, to rent the DVD of a
        movie, to stream a TV show over the internet, to repair a motorcycle, or
        to loan a book.
    """
    __schema_properties__ = Intangible.__schema_properties__ | {
        "acceptedPaymentMethod": ['r', "LoanOrCredit", "PaymentMethod", "Text"],
        "addOn": ['r', "Offer"],
        "additionalProperty": ['r', "PropertyValue"],
        "advanceBookingRequirement": "QuantitativeValue",
        "areaServed": ['r', "AdministrativeArea", "GeoShape", "Place", "Text"],
        "asin": "Text",
        "availability": "ItemAvailability",
        "availabilityEnds": ["DateTime", "Time"],
        "availabilityStarts": ["DateTime", "Time"],
        "availableAtOrFrom": "Place",
        "availableDeliveryMethod": "DeliveryMethod",
        "businessFunction": "BusinessFunction",
        "category": ['r', "OfferCategory", "CategoryCode", "PhysicalActivityCategory", "Thing", "Text"],
        "deliveryLeadTime": "QuantitativeValue",
        "eligibleCustomerType": "BusinessEntityType",
        "eligibleDuration": "QuantitativeValue",
        "eligibleQuantity": "QuantitativeValue",
        "eligibleRegion": ['r', "GeoShape", "Place", "Text"],
        "eligibleTransactionVolume": "PriceSpecification",
        "gtin": "Text",
        "gtin12": "Text",
        "gtin13": "Text",
        "gtin14": "Text",
        "gtin8": "Text",
        "hasAdultConsideration": ["AdultOrientedEnumeration"],
        "includesObject": "TypeAndQuantityNode",
        "ineligibleRegion": ['r', "GeoShape", "Place", "Text"],
        "inventoryLevel": "QuantitativeValue",
        "itemCondition": "OfferItemCondition",
        "itemOffered": "Product",  # Can also be Service but not in JSON-LD
        "mpn": "Text",
        "offeredBy": ["Organization", "Person"],
        "price": "Number",
        "priceCurrency": "Text",
        "priceSpecification": ['r', "PriceSpecification"],
        "priceValidUntil": "Date",
        "review": ['r', "Review"],
        "seller": ["Organization", "Person"],
        "serialNumber": "Text",
        "sku": "Text",
        "validFrom": "DateTime",
        "validThrough": "DateTime",
        "warranty": "WarrantyPromise"
    }

    def __init__(self,
                 availability: ItemAvailability,
                 price: float | None = None,
                 price_currency: str | None = None,
                 url: URL | str | None = None,
                 category: OfferCategory | None = None,
                 valid_from: DateTime | str | datetime | None = None,
                 valid_through: DateTime | str | datetime | None = None,
                 name: str | None = None, **kwargs) -> None:
        super().__init__(
            name=name,
            url=url,
            availability=availability,
            price=price,
            price_currency=price_currency,
            category=category,
            valid_from=valid_from,
            valid_through=valid_through,
             **kwargs
        )


class Quantity(Intangible):
    __description__ = """
        Quantities such as distance, time, mass, weight, etc. Particular
        instances of say Mass are entities like '3 kg' or '4 milligrams'.
    """


class Duration(Quantity):
    __description__ = "Quantity: Duration (use ISO 8601 duration format)."
    ISO_8601_PATTERN = re.compile(
        r"^P(?=\d|T)(?:(\d+)Y)?(?:(\d+)M)?(?:(\d+)D)?(?:T(?=\d)(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?$|^P(\d+)W$"
    )

    def __init__(self, value: str | timedelta) -> None:
        """
        Initialize a Duration instance.

        Args:
            value (str | timedelta): ISO 8601 duration string or timedelta object.

        Raises:
            ValueError: If the string format is invalid.
            TypeError: If the input type is not str or timedelta.
        """
        super().__init__()

        if isinstance(value, str):
            if not self.ISO_8601_PATTERN.match(value):
                raise ValueError(f"Invalid ISO 8601 duration format: {value}")
            self.value = value
        elif isinstance(value, timedelta):
            self.value = self.from_timedelta(value).value  # Convert timedelta to ISO 8601 format
        else:
            raise TypeError("Expected a string (ISO 8601) or a timedelta object.")

    @staticmethod
    def from_timedelta(td: timedelta) -> Duration:
        """
        Convert a Python timedelta object to an ISO 8601 duration format.

        Args:
            td (timedelta): The timedelta object to convert.

        Returns:
            Duration: A Duration instance representing the given timedelta.

        Raises:
            TypeError: If the input type is not str or timedelta.
        """
        if not isinstance(td, timedelta):
            raise TypeError("Expected a timedelta object.")

        total_seconds = int(td.total_seconds())
        days, remainder = divmod(total_seconds, 86400)  # 86400 seconds in a day
        hours, remainder = divmod(remainder, 3600)  # 3600 seconds in an hour
        minutes, seconds = divmod(remainder, 60)

        date_part = f"{days}D" if days else ""
        time_part = "".join(
            f"{value}{symbol}"
            for value, symbol in [(hours, "H"), (minutes, "M"), (seconds, "S")]
            if value
        )

        if date_part and time_part:
            iso_duration = f"P{date_part}T{time_part}"
        elif date_part:
            iso_duration = f"P{date_part}"
        elif time_part:
            iso_duration = f"PT{time_part}"
        else:
            iso_duration = "P0D"  # Default to zero duration

        return Duration(iso_duration)

    @staticmethod
    def from_components(num_years=None, num_months=None, num_days=None, num_weeks=None, num_hours=None, num_minutes=None, num_seconds=None) -> Duration:
        """
        Construct a Duration instance from individual time components.
        Returns:
            Duration
        """
        if num_weeks:
            return Duration(f"P{num_weeks}W")

        date_part = "".join(
            f"{value}{symbol}"
            for value, symbol in [
                (num_years, "Y"),
                (num_months, "M"),
                (num_days, "D"),
            ]
            if value
        )

        time_part = "".join(
            f"{value}{symbol}"
            for value, symbol in [
                (num_hours, "H"),
                (num_minutes, "M"),
                (num_seconds, "S"),
            ]
            if value
        )

        if date_part and time_part:
            return Duration(f"P{date_part}T{time_part}")
        elif date_part:
            return Duration(f"P{date_part}")
        elif time_part:
            return Duration(f"PT{time_part}")
        else:
            return Duration("P0D")  # Default to zero duration

    @staticmethod
    def is_valid_iso8601(duration_str: str) -> bool:
        """Check if a string is a valid ISO 8601 duration format.

        Args:
            duration_str (str): The duration string to validate.

        Returns:
            bool: True if valid, False otherwise.
        """
        return bool(Duration.ISO_8601_PATTERN.match(duration_str))
