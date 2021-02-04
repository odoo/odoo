const descriptionData = {
    websiteTypes: {1: {id: 1, label: 'a business website', name: 'business'},
                2: {id: 2, label: 'an online store', name: 'online_store'},
                3: {id: 3, label: 'a blog', name: 'blog'},
                4: {id: 4, label: 'an event website', name: 'event'},
                5: {id: 5, label: 'an elearning platform', name: 'elearning'}},
    websitePurposes: {1: {id: 1, label: 'get leads', name: 'get_leads'},
                    2: {id: 2, label: 'develop the brand', name: 'develop_brand'},
                    3: {id: 3, label: 'sell more', name: 'sell_more'},
                    4: {id: 4, label: 'inform customers', name: 'inform_customers'}},
    industries: [
        {
          "code": "abbey",
          "label": "abbey"
        },
        {
          "code": "aboriginal_and_torres_strait_islander_organisation",
          "label": "aboriginal and torres strait islander organisation"
        },
        {
          "code": "aboriginal_art_gallery",
          "label": "aboriginal art gallery"
        },
        {
          "code": "abortion_clinic",
          "label": "abortion clinic"
        },
        {
          "code": "abrasives_supplier",
          "label": "abrasives supplier"
        },
        {
          "code": "abundant_life_church",
          "label": "abundant life church"
        },
        {
          "code": "accountant",
          "label": "accountant"
        },
        {
          "code": "accounting_firm",
          "label": "accounting firm"
        },
        {
          "code": "accounting_school",
          "label": "accounting school"
        },
        {
          "code": "accounting_software_company",
          "label": "accounting software company"
        },
        {
          "code": "acoustical_consultant",
          "label": "acoustical consultant"
        },
        {
          "code": "acrobatic_diving_pool",
          "label": "acrobatic diving pool"
        },
        {
          "code": "acrylic_store",
          "label": "acrylic store"
        },
        {
          "code": "acupuncture_clinic",
          "label": "acupuncture clinic"
        },
        {
          "code": "acupuncture_school",
          "label": "acupuncture school"
        },
        {
          "code": "acupuncturist",
          "label": "acupuncturist"
        },
        {
          "code": "acura_dealer",
          "label": "acura dealer"
        },
        {
          "code": "addiction_treatment_center",
          "label": "addiction treatment center"
        },
        {
          "code": "administrative_attorney",
          "label": "administrative attorney"
        },
        {
          "code": "adoption_agency",
          "label": "adoption agency"
        },
        {
          "code": "adult_day_care_center",
          "label": "adult day care center"
        },
        {
          "code": "adult_dvd_store",
          "label": "adult dvd store"
        },
        {
          "code": "adult_education_school",
          "label": "adult education school"
        },
        {
          "code": "adult_entertainment_club",
          "label": "adult entertainment club"
        },
        {
          "code": "adult_entertainment_store",
          "label": "adult entertainment store"
        },
        {
          "code": "adult_foster_care_service",
          "label": "adult foster care service"
        },
        {
          "code": "adventure_sports",
          "label": "adventure sports"
        },
        {
          "code": "adventure_sports_center",
          "label": "adventure sports center"
        },
        {
          "code": "advertising_agency",
          "label": "advertising agency"
        },
        {
          "code": "advertising_photographer",
          "label": "commercial photographer"
        },
        {
          "code": "aerated_drinks_supplier",
          "label": "aerated drinks supplier"
        },
        {
          "code": "aerial_installation_service",
          "label": "antenna service"
        },
        {
          "code": "aerial_photographer",
          "label": "aerial photographer"
        },
        {
          "code": "aerial_sports_center",
          "label": "aerial sports center"
        },
        {
          "code": "aero_dance_class",
          "label": "aero dance class"
        },
        {
          "code": "aerobics_instructor",
          "label": "aerobics instructor"
        },
        {
          "code": "aeroclub",
          "label": "aeroclub"
        },
        {
          "code": "aeromodel_shop",
          "label": "aeromodel shop"
        },
        {
          "code": "aeronautical_engineer",
          "label": "aeronautical engineer"
        },
        {
          "code": "aerospace_company",
          "label": "aerospace company"
        },
        {
          "code": "afghani_restaurant",
          "label": "afghani restaurant"
        },
        {
          "code": "african_goods_store",
          "label": "african goods store"
        },
        {
          "code": "african_restaurant",
          "label": "african restaurant"
        },
        {
          "code": "after_school_program",
          "label": "after school program"
        },
        {
          "code": "agenzia_entrate",
          "label": "agenzia entrate"
        },
        {
          "code": "aggregate_supplier",
          "label": "aggregate supplier"
        },
        {
          "code": "agistment_service",
          "label": "agistment service"
        },
        {
          "code": "agricultural_association",
          "label": "agricultural association"
        },
        {
          "code": "agricultural_cooperative",
          "label": "agricultural cooperative"
        },
        {
          "code": "agricultural_engineer",
          "label": "agricultural engineer"
        },
        {
          "code": "agricultural_high_school",
          "label": "agricultural high school"
        },
        {
          "code": "agricultural_machinery_manufacturer",
          "label": "agricultural machinery manufacturer"
        },
        {
          "code": "agricultural_organization",
          "label": "agricultural organization"
        },
        {
          "code": "agricultural_product_wholesaler",
          "label": "agricultural product wholesaler"
        },
        {
          "code": "agricultural_production",
          "label": "agricultural production"
        },
        {
          "code": "agricultural_service",
          "label": "agricultural service"
        },
        {
          "code": "agricultural_service_supply_agency",
          "label": "agricultural service supply agency"
        },
        {
          "code": "agriculture_cooperative",
          "label": "agriculture cooperative"
        },
        {
          "code": "agrochemicals_supplier",
          "label": "agrochemicals supplier"
        },
        {
          "code": "aikido_club",
          "label": "aikido club"
        },
        {
          "code": "aikido_school",
          "label": "aikido school"
        },
        {
          "code": "air_compressor_repair_service",
          "label": "air compressor repair service"
        },
        {
          "code": "air_compressor_supplier",
          "label": "air compressor supplier"
        },
        {
          "code": "air_conditioning_contractor",
          "label": "air conditioning contractor"
        },
        {
          "code": "air_conditioning_repair_service",
          "label": "air conditioning repair service"
        },
        {
          "code": "air_conditioning_store",
          "label": "air conditioning store"
        },
        {
          "code": "air_conditioning_system_supplier",
          "label": "air conditioning system supplier"
        },
        {
          "code": "air_duct_cleaning_service",
          "label": "air duct cleaning service"
        },
        {
          "code": "air_filter_supplier",
          "label": "air filter supplier"
        },
        {
          "code": "air_force_base",
          "label": "air force base"
        },
        {
          "code": "air_taxi",
          "label": "air taxi"
        },
        {
          "code": "airbrushing_service",
          "label": "airbrushing service"
        },
        {
          "code": "airbrushing_supply_store",
          "label": "airbrushing supply store"
        },
        {
          "code": "aircraft_maintenance_company",
          "label": "aircraft maintenance company"
        },
        {
          "code": "aircraft_manufacturer",
          "label": "aircraft manufacturer"
        },
        {
          "code": "aircraft_rental_service",
          "label": "aircraft rental service"
        },
        {
          "code": "aircraft_supply_store",
          "label": "aircraft supply store"
        },
        {
          "code": "airline",
          "label": "airline"
        },
        {
          "code": "airline_ticket_agency",
          "label": "airline ticket agency"
        },
        {
          "code": "airplane_exhibit",
          "label": "airplane"
        },
        {
          "code": "airport",
          "label": "airport"
        },
        {
          "code": "airport_shuttle_service",
          "label": "airport shuttle service"
        },
        {
          "code": "airsoft_gun_shop",
          "label": "airsoft supply store"
        },
        {
          "code": "airstrip",
          "label": "airstrip"
        },
        {
          "code": "alcohol_manufacturer",
          "label": "alcohol manufacturer"
        },
        {
          "code": "alcohol_retail_monopoly",
          "label": "alcohol retail monopoly"
        },
        {
          "code": "alcoholic_beverage_wholesaler",
          "label": "alcoholic beverage wholesaler"
        },
        {
          "code": "alcoholism_treatment_program",
          "label": "alcoholism treatment program"
        },
        {
          "code": "alfa_romeo_dealer",
          "label": "alfa romeo dealer"
        },
        {
          "code": "allergist",
          "label": "allergist"
        },
        {
          "code": "alliance_church",
          "label": "alliance church"
        },
        {
          "code": "alsace_restaurant",
          "label": "alsace restaurant"
        },
        {
          "code": "alternative_fuel_station",
          "label": "alternative fuel station"
        },
        {
          "code": "alternative_medicine_practitioner",
          "label": "alternative medicine practitioner"
        },
        {
          "code": "alternator_supplier",
          "label": "alternator supplier"
        },
        {
          "code": "aluminium_supplier",
          "label": "aluminum supplier"
        },
        {
          "code": "aluminum_frames_supplier",
          "label": "aluminum frames supplier"
        },
        {
          "code": "aluminum_welder",
          "label": "aluminum welder"
        },
        {
          "code": "aluminum_window",
          "label": "aluminum window"
        },
        {
          "code": "amateur_theatre",
          "label": "amateur theater"
        },
        {
          "code": "ambulance_service",
          "label": "ambulance service"
        },
        {
          "code": "american_restaurant",
          "label": "american restaurant"
        },
        {
          "code": "amish_furniture_store",
          "label": "amish furniture store"
        },
        {
          "code": "ammunition_supplier",
          "label": "ammunition supplier"
        },
        {
          "code": "amphitheatre",
          "label": "amphitheater"
        },
        {
          "code": "amusement_center",
          "label": "amusement center"
        },
        {
          "code": "amusement_machine_supplier",
          "label": "amusement machine supplier"
        },
        {
          "code": "amusement_park",
          "label": "amusement park"
        },
        {
          "code": "amusement_park_ride",
          "label": "amusement park ride"
        },
        {
          "code": "amusement_ride_supplier",
          "label": "amusement ride supplier"
        },
        {
          "code": "an_hui_restaurant",
          "label": "anhui restaurant"
        },
        {
          "code": "anago_restaurant",
          "label": "anago restaurant"
        },
        {
          "code": "andalusian_restaurant",
          "label": "andalusian restaurant"
        },
        {
          "code": "anesthesiologist",
          "label": "anesthesiologist"
        },
        {
          "code": "angler_fish_restaurant",
          "label": "angler fish restaurant"
        },
        {
          "code": "anglican_church",
          "label": "anglican church"
        },
        {
          "code": "animal_control_service",
          "label": "animal control service"
        },
        {
          "code": "animal_hospital",
          "label": "animal hospital"
        },
        {
          "code": "animal_park",
          "label": "animal park"
        },
        {
          "code": "animal_protection_organization",
          "label": "animal protection organization"
        },
        {
          "code": "animal_rescue_service",
          "label": "animal rescue service"
        },
        {
          "code": "animal_shelter",
          "label": "animal shelter"
        },
        {
          "code": "animal_watering_hole",
          "label": "animal watering hole"
        },
        {
          "code": "animation_studio",
          "label": "animation studio"
        },
        {
          "code": "anime_club",
          "label": "anime club"
        },
        {
          "code": "anodizer",
          "label": "anodizer"
        },
        {
          "code": "antique_furniture_restoration_service",
          "label": "antique furniture restoration service"
        },
        {
          "code": "antique_furniture_store",
          "label": "antique furniture store"
        },
        {
          "code": "antique_store",
          "label": "antique store"
        },
        {
          "code": "apartment_building",
          "label": "apartment building"
        },
        {
          "code": "apartment_complex",
          "label": "apartment complex"
        },
        {
          "code": "apartment_rental_agency",
          "label": "apartment rental agency"
        },
        {
          "code": "apostolic_church",
          "label": "apostolic church"
        },
        {
          "code": "appliance_parts_supplier",
          "label": "appliance parts supplier"
        },
        {
          "code": "appliance_rental_service",
          "label": "appliance rental service"
        },
        {
          "code": "appliance_repair_service",
          "label": "appliance repair service"
        },
        {
          "code": "appliance_store",
          "label": "appliance store"
        },
        {
          "code": "appliances_customer_service",
          "label": "appliances customer service"
        },
        {
          "code": "appraiser",
          "label": "appraiser"
        },
        {
          "code": "apprenticeship_center",
          "label": "apprenticeship center"
        },
        {
          "code": "aquaculture_farm",
          "label": "aquaculture farm"
        },
        {
          "code": "aquarium",
          "label": "aquarium"
        },
        {
          "code": "aquarium_shop",
          "label": "aquarium shop"
        },
        {
          "code": "aquatic_center",
          "label": "aquatic centre"
        },
        {
          "code": "arboretum",
          "label": "arboretum"
        },
        {
          "code": "arborist_and_tree_surgeon",
          "label": "arborist and tree surgeon"
        },
        {
          "code": "archaeological_museum",
          "label": "archaeological museum"
        },
        {
          "code": "archery_club",
          "label": "archery club"
        },
        {
          "code": "archery_event",
          "label": "archery event"
        },
        {
          "code": "archery_hall",
          "label": "archery hall"
        },
        {
          "code": "archery_range",
          "label": "archery range"
        },
        {
          "code": "archery_store",
          "label": "archery store"
        },
        {
          "code": "architect",
          "label": "architect"
        },
        {
          "code": "architects_association",
          "label": "architects association"
        },
        {
          "code": "architectural_and_engineering_model_maker",
          "label": "architectural and engineering model maker"
        },
        {
          "code": "architectural_designer",
          "label": "architectural designer"
        },
        {
          "code": "architectural_salvage_store",
          "label": "architectural salvage store"
        },
        {
          "code": "architecture_firm",
          "label": "architecture firm"
        },
        {
          "code": "architecture_school",
          "label": "architecture school"
        },
        {
          "code": "archive",
          "label": "archive"
        },
        {
          "code": "arena",
          "label": "arena"
        },
        {
          "code": "argentinian_restaurant",
          "label": "argentinian restaurant"
        },
        {
          "code": "armed_forces_association",
          "label": "armed forces association"
        },
        {
          "code": "armenian_church",
          "label": "armenian church"
        },
        {
          "code": "armenian_restaurant",
          "label": "armenian restaurant"
        },
        {
          "code": "army_and_navy_store",
          "label": "army & navy surplus shop"
        },
        {
          "code": "army_base",
          "label": "army barracks"
        },
        {
          "code": "army_facility",
          "label": "army facility"
        },
        {
          "code": "army_museum",
          "label": "army museum"
        },
        {
          "code": "aromatherapy_class",
          "label": "aromatherapy class"
        },
        {
          "code": "aromatherapy_service",
          "label": "aromatherapy service"
        },
        {
          "code": "aromatherapy_supply_store",
          "label": "aromatherapy supply store"
        },
        {
          "code": "art_cafe",
          "label": "art cafe"
        },
        {
          "code": "art_center",
          "label": "art center"
        },
        {
          "code": "art_dealer",
          "label": "art dealer"
        },
        {
          "code": "art_gallery",
          "label": "art gallery"
        },
        {
          "code": "art_handcraft",
          "label": "art handcraft"
        },
        {
          "code": "art_museum",
          "label": "art museum"
        },
        {
          "code": "art_restoration_service",
          "label": "art restoration service"
        },
        {
          "code": "art_school",
          "label": "art school"
        },
        {
          "code": "art_studio",
          "label": "art studio"
        },
        {
          "code": "art_supply_store",
          "label": "art supply store"
        },
        {
          "code": "artificial_plant_supplier",
          "label": "artificial plant supplier"
        },
        {
          "code": "artist",
          "label": "artist"
        },
        {
          "code": "arts_organization",
          "label": "arts organization"
        },
        {
          "code": "asador",
          "label": "grill"
        },
        {
          "code": "asbestos_testing_service",
          "label": "asbestos testing service"
        },
        {
          "code": "ashram",
          "label": "ashram"
        },
        {
          "code": "asian_fusion_restaurant",
          "label": "asian fusion restaurant"
        },
        {
          "code": "asian_grocery_store",
          "label": "asian grocery store"
        },
        {
          "code": "asian_household_goods_store",
          "label": "asian household goods store"
        },
        {
          "code": "asian_restaurant",
          "label": "asian restaurant"
        },
        {
          "code": "asphalt_contractor",
          "label": "asphalt contractor"
        },
        {
          "code": "asphalt_mixing_plant",
          "label": "asphalt mixing plant"
        },
        {
          "code": "assemblies_of_god_church",
          "label": "assemblies of god church"
        },
        {
          "code": "assembly_room",
          "label": "assembly room"
        },
        {
          "code": "assistante_maternelle",
          "label": "assistante maternelle"
        },
        {
          "code": "assisted_living_facility",
          "label": "assisted living facility"
        },
        {
          "code": "association_or_organization",
          "label": "association or organization"
        },
        {
          "code": "aston_martin_dealer",
          "label": "aston martin dealer"
        },
        {
          "code": "astrologer",
          "label": "astrologer"
        },
        {
          "code": "asturian_restaurant",
          "label": "asturian restaurant"
        },
        {
          "code": "athletic_club",
          "label": "athletic club"
        },
        {
          "code": "athletic_field",
          "label": "athletic field"
        },
        {
          "code": "athletic_park",
          "label": "athletic park"
        },
        {
          "code": "athletic_track",
          "label": "athletic track"
        },
        {
          "code": "atm",
          "label": "atm"
        },
        {
          "code": "attorney_referral_service",
          "label": "attorney referral service"
        },
        {
          "code": "atv_dealer",
          "label": "atv dealer"
        },
        {
          "code": "atv_rental_service",
          "label": "atv rental service"
        },
        {
          "code": "atv_repair_shop",
          "label": "atv repair shop"
        },
        {
          "code": "auction_house",
          "label": "auction house"
        },
        {
          "code": "audi_dealer",
          "label": "audi dealer"
        },
        {
          "code": "audio_visual_consultant",
          "label": "audio visual consultant"
        },
        {
          "code": "audio_visual_equipment_rental_service",
          "label": "audio visual equipment rental service"
        },
        {
          "code": "audio_visual_equipment_repair_service",
          "label": "audio visual equipment repair service"
        },
        {
          "code": "audio_visual_equipment_supplier",
          "label": "audio visual equipment supplier"
        },
        {
          "code": "audiologist",
          "label": "audiologist"
        },
        {
          "code": "auditor",
          "label": "auditor"
        },
        {
          "code": "auditorium",
          "label": "auditorium"
        },
        {
          "code": "australian_goods_store",
          "label": "australian goods store"
        },
        {
          "code": "australian_restaurant",
          "label": "australian restaurant"
        },
        {
          "code": "austrian_restaurant",
          "label": "austrian restaurant"
        },
        {
          "code": "auto_accessories_wholesaler",
          "label": "auto accessories wholesaler"
        },
        {
          "code": "auto_air_conditioning_service",
          "label": "auto air conditioning service"
        },
        {
          "code": "auto_auction",
          "label": "auto auction"
        },
        {
          "code": "auto_body_parts_supplier",
          "label": "auto body parts supplier"
        },
        {
          "code": "auto_body_shop",
          "label": "auto body shop"
        },
        {
          "code": "auto_bodywork_mechanic",
          "label": "auto bodywork mechanic"
        },
        {
          "code": "auto_broker",
          "label": "auto broker"
        },
        {
          "code": "auto_chemistry_shop",
          "label": "auto chemistry shop"
        },
        {
          "code": "auto_dent_removal_service",
          "label": "auto dent removal service"
        },
        {
          "code": "auto_electrical_service",
          "label": "auto electrical service"
        },
        {
          "code": "auto_glass_shop",
          "label": "auto glass shop"
        },
        {
          "code": "auto_insurance_agency",
          "label": "auto insurance agency"
        },
        {
          "code": "auto_machine_shop",
          "label": "auto machine shop"
        },
        {
          "code": "auto_market",
          "label": "auto market"
        },
        {
          "code": "auto_parts_manufacturer",
          "label": "auto parts manufacturer"
        },
        {
          "code": "auto_parts_market",
          "label": "auto parts market"
        },
        {
          "code": "auto_parts_store",
          "label": "auto parts store"
        },
        {
          "code": "auto_radiator_repair_service",
          "label": "auto radiator repair service"
        },
        {
          "code": "auto_repair_shop",
          "label": "auto repair shop"
        },
        {
          "code": "auto_restoration_service",
          "label": "auto restoration service"
        },
        {
          "code": "auto_spring_shop",
          "label": "auto spring shop"
        },
        {
          "code": "auto_sunroof_shop",
          "label": "auto sunroof shop"
        },
        {
          "code": "auto_tag_agency",
          "label": "auto tag agency"
        },
        {
          "code": "auto_tune_up_service",
          "label": "auto tune up service"
        },
        {
          "code": "auto_upholsterer",
          "label": "auto upholsterer"
        },
        {
          "code": "auto_wrecker",
          "label": "auto wrecker"
        },
        {
          "code": "automation_company",
          "label": "automation company"
        },
        {
          "code": "automobile_storage_facility",
          "label": "automobile storage facility"
        },
        {
          "code": "aviation_consultant",
          "label": "aviation consultant"
        },
        {
          "code": "aviation_training_institute",
          "label": "aviation training institute"
        },
        {
          "code": "awning_supplier",
          "label": "awning supplier"
        },
        {
          "code": "baby_clothing_store",
          "label": "baby clothing store"
        },
        {
          "code": "baby_store",
          "label": "baby store"
        },
        {
          "code": "baby_swimming_school",
          "label": "baby swimming school"
        },
        {
          "code": "babysitter",
          "label": "childminder"
        },
        {
          "code": "badminton_club",
          "label": "badminton club"
        },
        {
          "code": "badminton_complex",
          "label": "badminton complex"
        },
        {
          "code": "badminton_court",
          "label": "badminton court"
        },
        {
          "code": "bag_shop",
          "label": "bag shop"
        },
        {
          "code": "bagel_shop",
          "label": "bagel shop"
        },
        {
          "code": "bahai_house_of_worship",
          "label": "bahai's house of worship"
        },
        {
          "code": "bail_bonds_service",
          "label": "bail bonds service"
        },
        {
          "code": "bailiff",
          "label": "bailiff"
        },
        {
          "code": "bait_shop",
          "label": "bait shop"
        },
        {
          "code": "bakery",
          "label": "bakery"
        },
        {
          "code": "bakery_equipment",
          "label": "bakery equipment"
        },
        {
          "code": "baking_supply_store",
          "label": "baking supply store"
        },
        {
          "code": "bakso_restaurant",
          "label": "bakso restaurant"
        },
        {
          "code": "balinese_restaurant",
          "label": "balinese restaurant"
        },
        {
          "code": "ballet_school",
          "label": "ballet school"
        },
        {
          "code": "ballet_theater",
          "label": "ballet theater"
        },
        {
          "code": "balloon_artist",
          "label": "balloon artist"
        },
        {
          "code": "balloon_ride_tour_agency",
          "label": "balloon ride tour agency"
        },
        {
          "code": "balloon_store",
          "label": "balloon store"
        },
        {
          "code": "ballroom_dance_instructor",
          "label": "ballroom dance instructor"
        },
        {
          "code": "band",
          "label": "band"
        },
        {
          "code": "bangladeshi_restaurant",
          "label": "bangladeshi restaurant"
        },
        {
          "code": "bank",
          "label": "bank"
        },
        {
          "code": "bankruptcy_attorney",
          "label": "bankruptcy attorney"
        },
        {
          "code": "bankruptcy_service",
          "label": "bankruptcy service"
        },
        {
          "code": "banner_store",
          "label": "banner store"
        },
        {
          "code": "banquet_hall",
          "label": "banquet hall"
        },
        {
          "code": "baptist_church",
          "label": "baptist church"
        },
        {
          "code": "bar",
          "label": "bar"
        },
        {
          "code": "bar_and_grill",
          "label": "bar & grill"
        },
        {
          "code": "bar_pmu",
          "label": "bar pmu"
        },
        {
          "code": "bar_restaurant_furniture_store",
          "label": "bar restaurant furniture store"
        },
        {
          "code": "bar_stool_supplier",
          "label": "bar stool supplier"
        },
        {
          "code": "bar_tabac",
          "label": "bar tabac"
        },
        {
          "code": "barbecue_restaurant",
          "label": "barbecue restaurant"
        },
        {
          "code": "barbecue_spots",
          "label": "barbecue area"
        },
        {
          "code": "barber_school",
          "label": "barber school"
        },
        {
          "code": "barber_shop",
          "label": "barber shop"
        },
        {
          "code": "barber_supply_store",
          "label": "barber supply store"
        },
        {
          "code": "bark_supplier",
          "label": "bark supplier"
        },
        {
          "code": "barrel_supplier",
          "label": "barrel supplier"
        },
        {
          "code": "barrister",
          "label": "barrister"
        },
        {
          "code": "bartending_school",
          "label": "bartending school"
        },
        {
          "code": "baseball",
          "label": "baseball"
        },
        {
          "code": "baseball_club",
          "label": "baseball club"
        },
        {
          "code": "baseball_field",
          "label": "baseball field"
        },
        {
          "code": "baseball_goods_store",
          "label": "baseball goods store"
        },
        {
          "code": "basilica",
          "label": "basilica"
        },
        {
          "code": "basket_supplier",
          "label": "basket supplier"
        },
        {
          "code": "basketball_club",
          "label": "basketball club"
        },
        {
          "code": "basketball_court",
          "label": "basketball court"
        },
        {
          "code": "basketball_court_contractor",
          "label": "basketball court contractor"
        },
        {
          "code": "basque_restaurant",
          "label": "basque restaurant"
        },
        {
          "code": "batak_restaurant",
          "label": "batak restaurant"
        },
        {
          "code": "bathroom_remodeler",
          "label": "bathroom remodeler"
        },
        {
          "code": "bathroom_supply_store",
          "label": "bathroom supply store"
        },
        {
          "code": "battery_manufacturer",
          "label": "battery manufacturer"
        },
        {
          "code": "battery_store",
          "label": "battery store"
        },
        {
          "code": "battery_wholesaler",
          "label": "battery wholesaler"
        },
        {
          "code": "batting_cage_center",
          "label": "batting cage center"
        },
        {
          "code": "bazar",
          "label": "bazar"
        },
        {
          "code": "bbq_area",
          "label": "bbq area"
        },
        {
          "code": "beach_cleaning_service",
          "label": "beach cleaning service"
        },
        {
          "code": "beach_clothing_store",
          "label": "beach clothing store"
        },
        {
          "code": "beach_entertainment_shop",
          "label": "beach entertainment shop"
        },
        {
          "code": "beach_pavillion",
          "label": "beach pavillion"
        },
        {
          "code": "beach_volleyball_club",
          "label": "beach volleyball club"
        },
        {
          "code": "beach_volleyball_court",
          "label": "beach volleyball court"
        },
        {
          "code": "bead_store",
          "label": "bead store"
        },
        {
          "code": "bead_wholesaler",
          "label": "bead wholesaler"
        },
        {
          "code": "bearing_supplier",
          "label": "bearing supplier"
        },
        {
          "code": "beautician",
          "label": "beautician"
        },
        {
          "code": "beauty_product_supplier",
          "label": "beauty product supplier"
        },
        {
          "code": "beauty_products_vending_machine",
          "label": "beauty products vending machine"
        },
        {
          "code": "beauty_products_wholesaler",
          "label": "beauty products wholesaler"
        },
        {
          "code": "beauty_salon",
          "label": "beauty salon"
        },
        {
          "code": "beauty_school",
          "label": "beauty school"
        },
        {
          "code": "beauty_supply_store",
          "label": "beauty supply store"
        },
        {
          "code": "bed_and_breakfast",
          "label": "bed & breakfast"
        },
        {
          "code": "bed_shop",
          "label": "bed shop"
        },
        {
          "code": "bedding_store",
          "label": "bedding store"
        },
        {
          "code": "bedroom_furniture_store",
          "label": "bedroom furniture store"
        },
        {
          "code": "beef_rice_bowl_restaurant",
          "label": "gyudon restaurant"
        },
        {
          "code": "beer_distributor",
          "label": "beer distributor"
        },
        {
          "code": "beer_garden",
          "label": "beer garden"
        },
        {
          "code": "beer_hall",
          "label": "beer hall"
        },
        {
          "code": "beer_store",
          "label": "beer store"
        },
        {
          "code": "belgian_restaurant",
          "label": "belgian restaurant"
        },
        {
          "code": "belt_shop",
          "label": "belt shop"
        },
        {
          "code": "bentley_dealer",
          "label": "bentley dealer"
        },
        {
          "code": "berry_restaurant",
          "label": "berry restaurant"
        },
        {
          "code": "betawi_restaurant",
          "label": "betawi restaurant"
        },
        {
          "code": "betting_agency",
          "label": "betting agency"
        },
        {
          "code": "beverage_distributor",
          "label": "beverage distributor"
        },
        {
          "code": "bicycle_club",
          "label": "bicycle club"
        },
        {
          "code": "bicycle_rack",
          "label": "bicycle rack"
        },
        {
          "code": "bicycle_rental_service",
          "label": "bicycle rental service"
        },
        {
          "code": "bicycle_repair_shop",
          "label": "bicycle repair shop"
        },
        {
          "code": "bicycle_store",
          "label": "bicycle store"
        },
        {
          "code": "bicycle_wholesale",
          "label": "bicycle wholesale"
        },
        {
          "code": "bikram_yoga_studio",
          "label": "bikram yoga studio"
        },
        {
          "code": "bilingual_school",
          "label": "bilingual school"
        },
        {
          "code": "billiards_supply_store",
          "label": "billiards supply store"
        },
        {
          "code": "bingo_hall",
          "label": "bingo hall"
        },
        {
          "code": "biochemical_supplier",
          "label": "biochemical supplier"
        },
        {
          "code": "biochemistry_lab",
          "label": "biochemistry lab"
        },
        {
          "code": "biofeedback_therapist",
          "label": "biofeedback therapist"
        },
        {
          "code": "biotechnology_company",
          "label": "biotechnology company"
        },
        {
          "code": "biotechnology_engineer",
          "label": "biotechnology engineer"
        },
        {
          "code": "bird_control_service",
          "label": "bird control service"
        },
        {
          "code": "bird_shop",
          "label": "bird shop"
        },
        {
          "code": "bird_watching_area",
          "label": "bird watching area"
        },
        {
          "code": "birth_center",
          "label": "birth center"
        },
        {
          "code": "birth_certificate_service",
          "label": "birth certificate service"
        },
        {
          "code": "birth_control_center",
          "label": "birth control center"
        },
        {
          "code": "biryani_restaurant",
          "label": "biryani restaurant"
        },
        {
          "code": "bistro",
          "label": "bistro"
        },
        {
          "code": "blacksmith",
          "label": "blacksmith"
        },
        {
          "code": "blast_cleaning_service",
          "label": "blast cleaning service"
        },
        {
          "code": "blind_school",
          "label": "blind school"
        },
        {
          "code": "blinds_shop",
          "label": "blinds shop"
        },
        {
          "code": "blood_bank",
          "label": "blood bank"
        },
        {
          "code": "blood_donation_center",
          "label": "blood donation center"
        },
        {
          "code": "blood_testing_service",
          "label": "blood testing service"
        },
        {
          "code": "blueprint_service",
          "label": "blueprint service"
        },
        {
          "code": "blues_club",
          "label": "blues club"
        },
        {
          "code": "bmw_dealer",
          "label": "bmw dealer"
        },
        {
          "code": "bmw_motorcycle_dealer",
          "label": "bmw motorcycle dealer"
        },
        {
          "code": "bmx_club",
          "label": "bmx club"
        },
        {
          "code": "bmx_park",
          "label": "bmx park"
        },
        {
          "code": "bmx_track",
          "label": "bmx track"
        },
        {
          "code": "board_game_club",
          "label": "board game club"
        },
        {
          "code": "board_of_education",
          "label": "board of education"
        },
        {
          "code": "board_of_trade",
          "label": "board of trade"
        },
        {
          "code": "boarding_house",
          "label": "boarding house"
        },
        {
          "code": "boarding_school",
          "label": "boarding school"
        },
        {
          "code": "boat_accessories_supplier",
          "label": "boat accessories supplier"
        },
        {
          "code": "boat_builder",
          "label": "boat builders"
        },
        {
          "code": "boat_club",
          "label": "boat club"
        },
        {
          "code": "boat_cover_supplier",
          "label": "boat cover supplier"
        },
        {
          "code": "boat_dealer",
          "label": "boat dealer"
        },
        {
          "code": "boat_ramp",
          "label": "boat ramp"
        },
        {
          "code": "boat_rental_service",
          "label": "boat rental service"
        },
        {
          "code": "boat_repair_shop",
          "label": "boat repair shop"
        },
        {
          "code": "boat_storage_facility",
          "label": "boat storage facility"
        },
        {
          "code": "boat_tour_agency",
          "label": "boat tour agency"
        },
        {
          "code": "boat_trailer_dealer",
          "label": "boat trailer dealer"
        },
        {
          "code": "boating_instructor",
          "label": "boating instructor"
        },
        {
          "code": "bocce_ball_court",
          "label": "bocce ball court"
        },
        {
          "code": "body_piercing_shop",
          "label": "body piercing shop"
        },
        {
          "code": "body_shaping_class",
          "label": "body shaping class"
        },
        {
          "code": "boiler_manufacturer",
          "label": "boiler manufacturer"
        },
        {
          "code": "boiler_supplier",
          "label": "boiler supplier"
        },
        {
          "code": "bonesetting_house",
          "label": "bonesetting house"
        },
        {
          "code": "bonsai_plant_supplier",
          "label": "bonsai plant supplier"
        },
        {
          "code": "book_publisher",
          "label": "book publisher"
        },
        {
          "code": "book_store",
          "label": "book store"
        },
        {
          "code": "bookbinder",
          "label": "bookbinder"
        },
        {
          "code": "bookkeeping_service",
          "label": "bookkeeping service"
        },
        {
          "code": "bookmaker",
          "label": "bookmaker"
        },
        {
          "code": "books_wholesaler",
          "label": "books wholesaler"
        },
        {
          "code": "boot_camp",
          "label": "boot camp"
        },
        {
          "code": "boot_repair_shop",
          "label": "boot repair shop"
        },
        {
          "code": "boot_store",
          "label": "boot store"
        },
        {
          "code": "border_crossing_station",
          "label": "border crossing station"
        },
        {
          "code": "border_guard",
          "label": "border guard"
        },
        {
          "code": "botanical_garden",
          "label": "botanical garden"
        },
        {
          "code": "bottle_and_can_redemption_center",
          "label": "bottle & can redemption center"
        },
        {
          "code": "bottled_water_supplier",
          "label": "bottled water supplier"
        },
        {
          "code": "bouncy_castle_hire",
          "label": "bouncy castle hire"
        },
        {
          "code": "boutique",
          "label": "boutique"
        },
        {
          "code": "bowling_alley",
          "label": "bowling alley"
        },
        {
          "code": "bowling_club",
          "label": "bowling club"
        },
        {
          "code": "bowling_supply_shop",
          "label": "bowling supply shop"
        },
        {
          "code": "box_lunch_supplier",
          "label": "box lunch supplier"
        },
        {
          "code": "boxing_club",
          "label": "boxing club"
        },
        {
          "code": "boxing_gym",
          "label": "boxing gym"
        },
        {
          "code": "boxing_ring",
          "label": "boxing ring"
        },
        {
          "code": "boys_high_school",
          "label": "boys' high school"
        },
        {
          "code": "bpo_company",
          "label": "bpo company"
        },
        {
          "code": "bpo_placement_agency",
          "label": "bpo placement agency"
        },
        {
          "code": "brake_shop",
          "label": "brake shop"
        },
        {
          "code": "brazilian_pastelaria",
          "label": "brazilian pastelaria"
        },
        {
          "code": "brazilian_restaurant",
          "label": "brazilian restaurant"
        },
        {
          "code": "breakfast_restaurant",
          "label": "breakfast restaurant"
        },
        {
          "code": "brewery",
          "label": "brewery"
        },
        {
          "code": "brewing_supply_store",
          "label": "brewing supply store"
        },
        {
          "code": "brewpub",
          "label": "brewpub"
        },
        {
          "code": "brick_manufacturer",
          "label": "brick manufacturer"
        },
        {
          "code": "bricklayer",
          "label": "bricklayer"
        },
        {
          "code": "bridal_shop",
          "label": "bridal shop"
        },
        {
          "code": "bridge",
          "label": "bridge"
        },
        {
          "code": "bridge_club",
          "label": "bridge club"
        },
        {
          "code": "british_restaurant",
          "label": "british restaurant"
        },
        {
          "code": "brunch_restaurant",
          "label": "brunch restaurant"
        },
        {
          "code": "bubble_tea_store",
          "label": "bubble tea store"
        },
        {
          "code": "buddhist_supplies_store",
          "label": "buddhist supplies store"
        },
        {
          "code": "buddhist_temple",
          "label": "buddhist temple"
        },
        {
          "code": "budget_japanese_inn",
          "label": "budget japanese inn"
        },
        {
          "code": "buffet_restaurant",
          "label": "buffet restaurant"
        },
        {
          "code": "bugatti_dealer",
          "label": "bugatti dealer"
        },
        {
          "code": "buick_dealer",
          "label": "buick dealer"
        },
        {
          "code": "building_consultant",
          "label": "building consultant"
        },
        {
          "code": "building_design_company",
          "label": "building design company"
        },
        {
          "code": "building_equipment_hire_service",
          "label": "building equipment hire service"
        },
        {
          "code": "building_firm",
          "label": "building firm"
        },
        {
          "code": "building_inspector",
          "label": "building inspector"
        },
        {
          "code": "building_materials_market",
          "label": "building materials market"
        },
        {
          "code": "building_materials_store",
          "label": "building materials store"
        },
        {
          "code": "building_materials_supplier",
          "label": "building materials supplier"
        },
        {
          "code": "building_restoration_service",
          "label": "building restoration service"
        },
        {
          "code": "building_society",
          "label": "building society"
        },
        {
          "code": "building_surveyor",
          "label": "chartered surveyor"
        },
        {
          "code": "bulgarian_restaurant",
          "label": "bulgarian restaurant"
        },
        {
          "code": "bullring",
          "label": "bullring"
        },
        {
          "code": "bungee_jumping_center",
          "label": "bungee jumping center"
        },
        {
          "code": "burglar_alarm_store",
          "label": "burglar alarm store"
        },
        {
          "code": "burmese_restaurant",
          "label": "burmese restaurant"
        },
        {
          "code": "burrito_restaurant",
          "label": "burrito restaurant"
        },
        {
          "code": "bus_and_coach_company",
          "label": "bus and coach company"
        },
        {
          "code": "bus_charter",
          "label": "bus charter"
        },
        {
          "code": "bus_company",
          "label": "bus company"
        },
        {
          "code": "bus_depot",
          "label": "bus depot"
        },
        {
          "code": "bus_ticket_agency",
          "label": "bus ticket agency"
        },
        {
          "code": "bus_tour_agency",
          "label": "bus tour agency"
        },
        {
          "code": "business_administration_service",
          "label": "business administration service"
        },
        {
          "code": "business_broker",
          "label": "business broker"
        },
        {
          "code": "business_center",
          "label": "business center"
        },
        {
          "code": "business_development_service",
          "label": "business development service"
        },
        {
          "code": "business_management_consultant",
          "label": "business management consultant"
        },
        {
          "code": "business_networking_company",
          "label": "business networking company"
        },
        {
          "code": "business_park",
          "label": "business park"
        },
        {
          "code": "business_school",
          "label": "business school"
        },
        {
          "code": "business_to_business_service",
          "label": "business to business service"
        },
        {
          "code": "butane_gas_supplier",
          "label": "butane gas supplier"
        },
        {
          "code": "butcher_shop",
          "label": "butcher shop"
        },
        {
          "code": "butcher_shop_deli",
          "label": "butcher shop deli"
        },
        {
          "code": "butsudan_store",
          "label": "butsudan store"
        },
        {
          "code": "cabaret_club",
          "label": "cabaret club"
        },
        {
          "code": "cabin_rental_agency",
          "label": "cabin rental agency"
        },
        {
          "code": "cabinet_maker",
          "label": "cabinet maker"
        },
        {
          "code": "cabinet_store",
          "label": "cabinet store"
        },
        {
          "code": "cable_company",
          "label": "cable company"
        },
        {
          "code": "cadillac_dealer",
          "label": "cadillac dealer"
        },
        {
          "code": "cafe",
          "label": "cafe"
        },
        {
          "code": "cafeteria",
          "label": "cafeteria"
        },
        {
          "code": "cajun_restaurant",
          "label": "cajun restaurant"
        },
        {
          "code": "cake_decorating_equipment_shop",
          "label": "cake decorating equipment shop"
        },
        {
          "code": "cake_shop",
          "label": "cake shop"
        },
        {
          "code": "californian_restaurant",
          "label": "californian restaurant"
        },
        {
          "code": "call_center",
          "label": "call center"
        },
        {
          "code": "call_shop",
          "label": "call shop"
        },
        {
          "code": "calligraphy_lesson",
          "label": "calligraphy lesson"
        },
        {
          "code": "calvary_chapel_church",
          "label": "calvary chapel church"
        },
        {
          "code": "cambodian_restaurant",
          "label": "cambodian restaurant"
        },
        {
          "code": "camera_repair_shop",
          "label": "camera repair shop"
        },
        {
          "code": "camera_store",
          "label": "camera store"
        },
        {
          "code": "camp",
          "label": "camp"
        },
        {
          "code": "camper_shell_supplier",
          "label": "camper shell supplier"
        },
        {
          "code": "campground",
          "label": "campground"
        },
        {
          "code": "camping_cabin",
          "label": "camping cabin"
        },
        {
          "code": "camping_farm",
          "label": "camping farm"
        },
        {
          "code": "camping_store",
          "label": "camping store"
        },
        {
          "code": "canadian_pacific_northwest_restaurant",
          "label": "pacific northwest restaurant (canada)"
        },
        {
          "code": "canadian_restaurant",
          "label": "canadian restaurant"
        },
        {
          "code": "cancer_treatment_center",
          "label": "cancer treatment center"
        },
        {
          "code": "candle_store",
          "label": "candle store"
        },
        {
          "code": "candy_store",
          "label": "candy store"
        },
        {
          "code": "cane_furniture_store",
          "label": "cane furniture store"
        },
        {
          "code": "cannabis_store",
          "label": "cannabis store"
        },
        {
          "code": "cannery",
          "label": "cannery"
        },
        {
          "code": "canoe_and_kayak_club",
          "label": "canoe and kayak club"
        },
        {
          "code": "canoe_and_kayak_rental_service",
          "label": "canoe & kayak rental service"
        },
        {
          "code": "canoe_and_kayak_store",
          "label": "canoe & kayak store"
        },
        {
          "code": "canoe_and_kayak_tour_agency",
          "label": "canoe & kayak tour agency"
        },
        {
          "code": "canoeing_area",
          "label": "canoeing area"
        },
        {
          "code": "cantabrian_restaurant",
          "label": "cantabrian restaurant"
        },
        {
          "code": "cantonese_restaurant",
          "label": "cantonese restaurant"
        },
        {
          "code": "cape_verdean_restaurant",
          "label": "cape verdean restaurant"
        },
        {
          "code": "capoeira_school",
          "label": "capoeira school"
        },
        {
          "code": "capsule_hotel",
          "label": "capsule hotel"
        },
        {
          "code": "car_accessories_store",
          "label": "car accessories store"
        },
        {
          "code": "car_alarm_supplier",
          "label": "car alarm supplier"
        },
        {
          "code": "car_battery_store",
          "label": "car battery store"
        },
        {
          "code": "car_dealer",
          "label": "car dealer"
        },
        {
          "code": "car_detailing_service",
          "label": "car detailing service"
        },
        {
          "code": "car_factory",
          "label": "car factory"
        },
        {
          "code": "car_finance_and_loan_company",
          "label": "car finance and loan company"
        },
        {
          "code": "car_inspection_station",
          "label": "car inspection station"
        },
        {
          "code": "car_leasing_service",
          "label": "car leasing service"
        },
        {
          "code": "car_manufacturer",
          "label": "car manufacturer"
        },
        {
          "code": "car_race_track",
          "label": "car racing track"
        },
        {
          "code": "car_rental_agency",
          "label": "car rental agency"
        },
        {
          "code": "car_repair",
          "label": "car repair and maintenance"
        },
        {
          "code": "car_security_system_installer",
          "label": "car security system installer"
        },
        {
          "code": "car_service",
          "label": "car service"
        },
        {
          "code": "car_sharing_location",
          "label": "car sharing location"
        },
        {
          "code": "car_stereo_store",
          "label": "car stereo store"
        },
        {
          "code": "car_wash",
          "label": "car wash"
        },
        {
          "code": "carabinieri_police",
          "label": "carabinieri police"
        },
        {
          "code": "cardiologist",
          "label": "cardiologist"
        },
        {
          "code": "career_guidance_service",
          "label": "career guidance service"
        },
        {
          "code": "caribbean_restaurant",
          "label": "caribbean restaurant"
        },
        {
          "code": "carnival_club",
          "label": "carnival club"
        },
        {
          "code": "carpenter",
          "label": "carpenter"
        },
        {
          "code": "carpet_cleaning_service",
          "label": "carpet cleaning service"
        },
        {
          "code": "carpet_installer",
          "label": "carpet installer"
        },
        {
          "code": "carpet_manufacturer",
          "label": "carpet manufacturer"
        },
        {
          "code": "carpet_store",
          "label": "carpet store"
        },
        {
          "code": "carpet_wholesaler",
          "label": "carpet wholesaler"
        },
        {
          "code": "carpool",
          "label": "carpool"
        },
        {
          "code": "carport_and_pergola_builder",
          "label": "carport and pergola builder"
        },
        {
          "code": "carriage_ride_service",
          "label": "carriage ride service"
        },
        {
          "code": "carvery_restaurant",
          "label": "carvery"
        },
        {
          "code": "cash_and_carry_wholesaler",
          "label": "cash and carry wholesaler"
        },
        {
          "code": "casino",
          "label": "casino"
        },
        {
          "code": "casket_service",
          "label": "casket service"
        },
        {
          "code": "castilian_restaurant",
          "label": "castilian restaurant"
        },
        {
          "code": "castle",
          "label": "castle"
        },
        {
          "code": "casual_japanese_style_restaurant",
          "label": "syokudo and teishoku restaurant"
        },
        {
          "code": "casual_sushi_restaurant",
          "label": "conveyor belt sushi restaurant"
        },
        {
          "code": "cat_hostel",
          "label": "cat hostel"
        },
        {
          "code": "catalonian_restaurant",
          "label": "catalonian restaurant"
        },
        {
          "code": "catering_food_and_drink_supplies",
          "label": "catering food and drink supplier"
        },
        {
          "code": "catering_service",
          "label": "caterer"
        },
        {
          "code": "cathedral",
          "label": "cathedral"
        },
        {
          "code": "catholic_cathedral",
          "label": "catholic cathedral"
        },
        {
          "code": "catholic_church",
          "label": "catholic church"
        },
        {
          "code": "catholic_school",
          "label": "catholic school"
        },
        {
          "code": "cattery",
          "label": "cattery"
        },
        {
          "code": "cattle_farm",
          "label": "cattle farm"
        },
        {
          "code": "cattle_market",
          "label": "cattle market"
        },
        {
          "code": "cbse_school",
          "label": "cbse school"
        },
        {
          "code": "cd_store",
          "label": "cd store"
        },
        {
          "code": "ceiling_supplier",
          "label": "ceiling supplier"
        },
        {
          "code": "cell_phone_accessory_store",
          "label": "cell phone accessory store"
        },
        {
          "code": "cell_phone_charging_station",
          "label": "cell phone charging station"
        },
        {
          "code": "cell_phone_store",
          "label": "cell phone store"
        },
        {
          "code": "cement_manufacturer",
          "label": "cement manufacturer"
        },
        {
          "code": "cement_supplier",
          "label": "cement supplier"
        },
        {
          "code": "cemetery",
          "label": "cemetery"
        },
        {
          "code": "central_american_restaurant",
          "label": "central american restaurant"
        },
        {
          "code": "central_authority",
          "label": "central authority"
        },
        {
          "code": "central_bank",
          "label": "central bank"
        },
        {
          "code": "central_javanese_restaurant",
          "label": "central javanese restaurant"
        },
        {
          "code": "ceramic_manufacturer",
          "label": "ceramic manufacturer"
        },
        {
          "code": "ceramics_wholesaler",
          "label": "ceramics wholesaler"
        },
        {
          "code": "certification_agency",
          "label": "certification agency"
        },
        {
          "code": "certified_public_accountant",
          "label": "certified public accountant"
        },
        {
          "code": "chalet",
          "label": "chalet"
        },
        {
          "code": "chamber_of_agriculture",
          "label": "chamber of agriculture"
        },
        {
          "code": "chamber_of_commerce",
          "label": "chamber of commerce"
        },
        {
          "code": "chamber_of_handicrafts",
          "label": "chamber of handicrafts"
        },
        {
          "code": "champon_noodle_restaurant",
          "label": "champon noodle restaurant"
        },
        {
          "code": "chankonabe_restaurant",
          "label": "chanko restaurant"
        },
        {
          "code": "chapel",
          "label": "chapel"
        },
        {
          "code": "charcuterie",
          "label": "charcuterie"
        },
        {
          "code": "charity",
          "label": "charity"
        },
        {
          "code": "charter_school",
          "label": "charter school"
        },
        {
          "code": "chartered_accountant",
          "label": "chartered accountant"
        },
        {
          "code": "check_cashing_service",
          "label": "check cashing service"
        },
        {
          "code": "cheese_manufacturer",
          "label": "cheese manufacturer"
        },
        {
          "code": "cheese_shop",
          "label": "cheese shop"
        },
        {
          "code": "cheesesteak_restaurant",
          "label": "cheesesteak restaurant"
        },
        {
          "code": "chemical_engineer",
          "label": "chemical engineer"
        },
        {
          "code": "chemical_exporter",
          "label": "chemical exporter"
        },
        {
          "code": "chemical_manufacturer",
          "label": "chemical manufacturer"
        },
        {
          "code": "chemical_plant",
          "label": "chemical plant"
        },
        {
          "code": "chemical_wholesaler",
          "label": "chemical wholesaler"
        },
        {
          "code": "chemistry_faculty",
          "label": "chemistry faculty"
        },
        {
          "code": "chemistry_lab",
          "label": "chemistry lab"
        },
        {
          "code": "chesapeake_restaurant",
          "label": "chesapeake restaurant"
        },
        {
          "code": "chess_and_card_club",
          "label": "chess and card club"
        },
        {
          "code": "chess_club",
          "label": "chess club"
        },
        {
          "code": "chess_instructor",
          "label": "chess instructor"
        },
        {
          "code": "chettinad_restaurtant",
          "label": "chettinad restaurant"
        },
        {
          "code": "chevrolet_dealer",
          "label": "chevrolet dealer"
        },
        {
          "code": "chicken_hatchery",
          "label": "chicken hatchery"
        },
        {
          "code": "chicken_restaurant",
          "label": "chicken restaurant"
        },
        {
          "code": "chicken_shop",
          "label": "chicken shop"
        },
        {
          "code": "chicken_wings_restaurant",
          "label": "chicken wings restaurant"
        },
        {
          "code": "child_care_agency",
          "label": "child care agency"
        },
        {
          "code": "child_health_care_centre",
          "label": "child health care centre"
        },
        {
          "code": "child_psychologist",
          "label": "child psychologist"
        },
        {
          "code": "childbirth_class",
          "label": "childbirth class"
        },
        {
          "code": "children_amusement_center",
          "label": "children's amusement center"
        },
        {
          "code": "children_hall",
          "label": "children hall"
        },
        {
          "code": "children_policlinic",
          "label": "children policlinic"
        },
        {
          "code": "childrens_book_store",
          "label": "childrens book store"
        },
        {
          "code": "childrens_cafe",
          "label": "childrens cafe"
        },
        {
          "code": "childrens_clothing_store",
          "label": "children's clothing store"
        },
        {
          "code": "childrens_club",
          "label": "childrens club"
        },
        {
          "code": "childrens_farm",
          "label": "childrens farm"
        },
        {
          "code": "childrens_furniture_store",
          "label": "children's furniture store"
        },
        {
          "code": "childrens_home",
          "label": "childrens home"
        },
        {
          "code": "childrens_hospital",
          "label": "children's hospital"
        },
        {
          "code": "childrens_library",
          "label": "childrens library"
        },
        {
          "code": "childrens_museum",
          "label": "children's museum"
        },
        {
          "code": "childrens_party_buffet",
          "label": "childrens party buffet"
        },
        {
          "code": "childrens_party_service",
          "label": "children's party service"
        },
        {
          "code": "childrens_store",
          "label": "childrens store"
        },
        {
          "code": "childrens_theater",
          "label": "childrens theater"
        },
        {
          "code": "chilean_restaurant",
          "label": "chilean restaurant"
        },
        {
          "code": "chimney_services",
          "label": "chimney services"
        },
        {
          "code": "chimney_sweep",
          "label": "chimney sweep"
        },
        {
          "code": "chinaware_store",
          "label": "chinaware store"
        },
        {
          "code": "chinese_language_instructor",
          "label": "chinese language instructor"
        },
        {
          "code": "chinese_language_school",
          "label": "chinese language school"
        },
        {
          "code": "chinese_medicine_clinic",
          "label": "chinese medicine clinic"
        },
        {
          "code": "chinese_medicine_store",
          "label": "chinese medicine store"
        },
        {
          "code": "chinese_noodle_restaurant",
          "label": "chinese noodle restaurant"
        },
        {
          "code": "chinese_pastry",
          "label": "chinese pastry"
        },
        {
          "code": "chinese_restaurant",
          "label": "chinese restaurant"
        },
        {
          "code": "chinese_supermarket",
          "label": "chinese supermarket"
        },
        {
          "code": "chinese_takeaway",
          "label": "chinese takeaway"
        },
        {
          "code": "chinese_tea_house",
          "label": "chinese tea house"
        },
        {
          "code": "chiropractor",
          "label": "chiropractor"
        },
        {
          "code": "chocolate_artisan",
          "label": "chocolate artisan"
        },
        {
          "code": "chocolate_cafe",
          "label": "chocolate cafe"
        },
        {
          "code": "chocolate_factory",
          "label": "chocolate factory"
        },
        {
          "code": "chocolate_shop",
          "label": "chocolate shop"
        },
        {
          "code": "choir",
          "label": "choir"
        },
        {
          "code": "chophouse_restaurant",
          "label": "chophouse restaurant"
        },
        {
          "code": "christian_book_store",
          "label": "christian book store"
        },
        {
          "code": "christian_church",
          "label": "christian church"
        },
        {
          "code": "christian_college",
          "label": "christian college"
        },
        {
          "code": "christmas_market",
          "label": "christmas market"
        },
        {
          "code": "christmas_store",
          "label": "christmas store"
        },
        {
          "code": "christmas_tree_farm",
          "label": "christmas tree farm"
        },
        {
          "code": "chrysler_dealer",
          "label": "chrysler dealer"
        },
        {
          "code": "church",
          "label": "church"
        },
        {
          "code": "church_of_christ",
          "label": "church of christ"
        },
        {
          "code": "church_of_jesus_christ_of_latter_day_saints",
          "label": "church of jesus christ of latter-day saints"
        },
        {
          "code": "church_of_the_nazarene",
          "label": "church of the nazarene"
        },
        {
          "code": "church_supply_store",
          "label": "church supply store"
        },
        {
          "code": "churreria",
          "label": "churreria"
        },
        {
          "code": "cider_bar",
          "label": "cider bar"
        },
        {
          "code": "cider_mill",
          "label": "cider mill"
        },
        {
          "code": "cigar_shop",
          "label": "cigar shop"
        },
        {
          "code": "cinema_equipment_supplier",
          "label": "cinema equipment supplier"
        },
        {
          "code": "circular_distribution_service",
          "label": "circular distribution service"
        },
        {
          "code": "circus",
          "label": "circus"
        },
        {
          "code": "citizen_information_bureau",
          "label": "citizen information bureau"
        },
        {
          "code": "citizens_advice_bureau",
          "label": "citizens advice bureau"
        },
        {
          "code": "citroen_dealer",
          "label": "citroen dealer"
        },
        {
          "code": "city_administration",
          "label": "city administration"
        },
        {
          "code": "city_clerks_office",
          "label": "city clerk's office"
        },
        {
          "code": "city_courthouse",
          "label": "city courthouse"
        },
        {
          "code": "city_department_of_environment",
          "label": "city department of environment"
        },
        {
          "code": "city_department_of_public_safety",
          "label": "city department of public safety"
        },
        {
          "code": "city_department_of_transportation",
          "label": "city department of transportation"
        },
        {
          "code": "city_district_office",
          "label": "city district office"
        },
        {
          "code": "city_employment_department",
          "label": "city employment department"
        },
        {
          "code": "city_government_office",
          "label": "city government office"
        },
        {
          "code": "city_hall",
          "label": "city or town hall"
        },
        {
          "code": "city_park",
          "label": "city park"
        },
        {
          "code": "city_pillar_shine",
          "label": "city pillar shrine"
        },
        {
          "code": "city_tax_office",
          "label": "city tax office"
        },
        {
          "code": "civic_center",
          "label": "civic center"
        },
        {
          "code": "civil_defence",
          "label": "civil defense"
        },
        {
          "code": "civil_engineer",
          "label": "civil engineer"
        },
        {
          "code": "civil_engineering_company",
          "label": "civil engineering company"
        },
        {
          "code": "civil_examinations_academy",
          "label": "civil examinations academy"
        },
        {
          "code": "civil_law_attorney",
          "label": "civil law attorney"
        },
        {
          "code": "civil_police",
          "label": "civil police"
        },
        {
          "code": "civil_registry",
          "label": "civil registry"
        },
        {
          "code": "class",
          "label": "class"
        },
        {
          "code": "classified_ads_newspaper_publisher",
          "label": "classified ads newspaper publisher"
        },
        {
          "code": "cleaners",
          "label": "cleaners"
        },
        {
          "code": "cleaning_products_supplier",
          "label": "cleaning products supplier"
        },
        {
          "code": "clergyman",
          "label": "clergyman"
        },
        {
          "code": "clock_repair_service",
          "label": "clock repair service"
        },
        {
          "code": "clock_watch_maker",
          "label": "clock watch maker"
        },
        {
          "code": "closed_circuit_television",
          "label": "closed circuit television"
        },
        {
          "code": "clothes_and_fabric_manufacturer",
          "label": "clothes and fabric manufacturer"
        },
        {
          "code": "clothes_and_fabric_wholesaler",
          "label": "clothes and fabric wholesaler"
        },
        {
          "code": "clothes_market",
          "label": "clothes market"
        },
        {
          "code": "clothing_alteration_service",
          "label": "clothing alteration service"
        },
        {
          "code": "clothing_store",
          "label": "clothing store"
        },
        {
          "code": "clothing_supplier",
          "label": "clothing supplier"
        },
        {
          "code": "clothing_wholesale_market_place",
          "label": "clothing wholesale market place"
        },
        {
          "code": "clothing_wholesaler",
          "label": "clothing wholesaler"
        },
        {
          "code": "club",
          "label": "club"
        },
        {
          "code": "cng_fittment_center",
          "label": "cng fittment center"
        },
        {
          "code": "coaching_center",
          "label": "coaching center"
        },
        {
          "code": "coal_exporter",
          "label": "coal exporter"
        },
        {
          "code": "coal_supplier",
          "label": "coal supplier"
        },
        {
          "code": "coalfield",
          "label": "coalfield"
        },
        {
          "code": "coast_guard_station",
          "label": "coast guard station"
        },
        {
          "code": "coat_wholesaler",
          "label": "coat wholesaler"
        },
        {
          "code": "cocktail_bar",
          "label": "cocktail bar"
        },
        {
          "code": "coed_school",
          "label": "co-ed school"
        },
        {
          "code": "coffee_machine_supplier",
          "label": "coffee machine supplier"
        },
        {
          "code": "coffee_roasters",
          "label": "coffee roasters"
        },
        {
          "code": "coffee_shop",
          "label": "coffee shop"
        },
        {
          "code": "coffee_stand",
          "label": "coffee stand"
        },
        {
          "code": "coffee_store",
          "label": "coffee store"
        },
        {
          "code": "coffee_vending_machine",
          "label": "coffee vending machine"
        },
        {
          "code": "coffee_wholesaler",
          "label": "coffee wholesaler"
        },
        {
          "code": "coffin_supplier",
          "label": "coffin supplier"
        },
        {
          "code": "coin_dealer",
          "label": "coin dealer"
        },
        {
          "code": "coin_operated_laundry_equipment_supplier",
          "label": "coin operated laundry equipment supplier"
        },
        {
          "code": "coin_operated_locker",
          "label": "coin operated locker"
        },
        {
          "code": "cold_cut_store",
          "label": "cold cut store"
        },
        {
          "code": "cold_noodle_restaurant",
          "label": "cold noodle restaurant"
        },
        {
          "code": "cold_storage_facility",
          "label": "cold storage facility"
        },
        {
          "code": "collectibles_store",
          "label": "collectibles store"
        },
        {
          "code": "college",
          "label": "college"
        },
        {
          "code": "college_of_agriculture",
          "label": "college of agriculture"
        },
        {
          "code": "colombian_restaurant",
          "label": "colombian restaurant"
        },
        {
          "code": "comedy_club",
          "label": "comedy club"
        },
        {
          "code": "comic_book_store",
          "label": "comic book store"
        },
        {
          "code": "comic_cafe",
          "label": "comic cafe"
        },
        {
          "code": "commercial_agent",
          "label": "commercial agent"
        },
        {
          "code": "commercial_cleaning_service",
          "label": "commercial cleaning service"
        },
        {
          "code": "commercial_printer",
          "label": "commercial printer"
        },
        {
          "code": "commercial_real_estate_agency",
          "label": "commercial real estate agency"
        },
        {
          "code": "commercial_real_estate_inspector",
          "label": "commercial real estate inspector"
        },
        {
          "code": "commercial_refrigeration",
          "label": "commercial refrigeration"
        },
        {
          "code": "commercial_refrigerator_supplier",
          "label": "commercial refrigerator supplier"
        },
        {
          "code": "commissioner_for_oaths",
          "label": "commissioner for oaths"
        },
        {
          "code": "communications_central",
          "label": "communications central"
        },
        {
          "code": "community_center",
          "label": "community center"
        },
        {
          "code": "community_college",
          "label": "community college"
        },
        {
          "code": "community_garden",
          "label": "community garden"
        },
        {
          "code": "community_health_center",
          "label": "community health centre"
        },
        {
          "code": "community_school",
          "label": "community school"
        },
        {
          "code": "company_registry",
          "label": "company registry"
        },
        {
          "code": "computer_accessories_store",
          "label": "computer accessories store"
        },
        {
          "code": "computer_club",
          "label": "computer club"
        },
        {
          "code": "computer_consultant",
          "label": "computer consultant"
        },
        {
          "code": "computer_desk_store",
          "label": "computer desk store"
        },
        {
          "code": "computer_hardware_manufacturer",
          "label": "computer hardware manufacturer"
        },
        {
          "code": "computer_networking_center",
          "label": "computer networking center"
        },
        {
          "code": "computer_repair_service",
          "label": "computer repair service"
        },
        {
          "code": "computer_security_service",
          "label": "computer security service"
        },
        {
          "code": "computer_service",
          "label": "computer service"
        },
        {
          "code": "computer_software_store",
          "label": "computer software store"
        },
        {
          "code": "computer_store",
          "label": "computer store"
        },
        {
          "code": "computer_support_and_services",
          "label": "computer support and services"
        },
        {
          "code": "computer_training_school",
          "label": "computer training school"
        },
        {
          "code": "computer_wholesaler",
          "label": "computer wholesaler"
        },
        {
          "code": "concert_hall",
          "label": "concert hall"
        },
        {
          "code": "concrete_contractor",
          "label": "concrete contractor"
        },
        {
          "code": "concrete_factory",
          "label": "concrete factory"
        },
        {
          "code": "concrete_metal_framework_supplier",
          "label": "concrete metal framework supplier"
        },
        {
          "code": "concrete_product_supplier",
          "label": "concrete product supplier"
        },
        {
          "code": "condiments_supplier",
          "label": "condiments supplier"
        },
        {
          "code": "condominium_complex",
          "label": "condominium complex"
        },
        {
          "code": "condominium_rental_agency",
          "label": "condominium rental agency"
        },
        {
          "code": "confectionery",
          "label": "confectionery"
        },
        {
          "code": "confectionery_wholesaler",
          "label": "confectionery wholesaler"
        },
        {
          "code": "conference_center",
          "label": "conference center"
        },
        {
          "code": "congregation",
          "label": "congregation"
        },
        {
          "code": "conservation_department",
          "label": "conservation department"
        },
        {
          "code": "conservative_club",
          "label": "conservative club"
        },
        {
          "code": "conservative_synagogue",
          "label": "conservative synagogue"
        },
        {
          "code": "conservatory_construction_contractor",
          "label": "conservatory construction contractor"
        },
        {
          "code": "conservatory_of_music",
          "label": "conservatory of music"
        },
        {
          "code": "conservatory_specialist",
          "label": "conservatory supply & installation"
        },
        {
          "code": "consignment_shop",
          "label": "consignment shop"
        },
        {
          "code": "construction_and_maintenance_office",
          "label": "construction and maintenance office"
        },
        {
          "code": "construction_company",
          "label": "construction company"
        },
        {
          "code": "construction_equipment_supplier",
          "label": "construction equipment supplier"
        },
        {
          "code": "construction_machine_dealer",
          "label": "construction machine dealer"
        },
        {
          "code": "construction_machine_rental_service",
          "label": "construction machine rental service"
        },
        {
          "code": "construction_material_wholesaler",
          "label": "construction material wholesaler"
        },
        {
          "code": "consultant",
          "label": "consultant"
        },
        {
          "code": "consumer_advice_center",
          "label": "consumer advice center"
        },
        {
          "code": "contact_lenses_supplier",
          "label": "contact lenses supplier"
        },
        {
          "code": "container_service",
          "label": "container service"
        },
        {
          "code": "container_supplier",
          "label": "container supplier"
        },
        {
          "code": "container_terminal",
          "label": "container terminal"
        },
        {
          "code": "containers_supplier",
          "label": "containers supplier"
        },
        {
          "code": "contemporary_louisiana_restaurant",
          "label": "contemporary louisiana restaurant"
        },
        {
          "code": "continental_restaurant",
          "label": "continental restaurant"
        },
        {
          "code": "contractor",
          "label": "contractor"
        },
        {
          "code": "convenience_store",
          "label": "convenience store"
        },
        {
          "code": "convenience_stores_organization",
          "label": "convenience stores organization"
        },
        {
          "code": "convention_center",
          "label": "convention center"
        },
        {
          "code": "convention_information_bureau",
          "label": "convention information bureau"
        },
        {
          "code": "conveyancer",
          "label": "conveyancer"
        },
        {
          "code": "cookie_shop",
          "label": "cookie shop"
        },
        {
          "code": "cooking_class",
          "label": "cooking class"
        },
        {
          "code": "cooking_school",
          "label": "cooking school"
        },
        {
          "code": "cooling_plant",
          "label": "cooling plant"
        },
        {
          "code": "copier_repair_service",
          "label": "copier repair service"
        },
        {
          "code": "copper_supplier",
          "label": "copper supplier"
        },
        {
          "code": "coppersmith",
          "label": "coppersmith"
        },
        {
          "code": "copy_shop",
          "label": "copy shop"
        },
        {
          "code": "copying_supply_store",
          "label": "copying supply store"
        },
        {
          "code": "corporate_campus",
          "label": "corporate campus"
        },
        {
          "code": "corporate_entertainment_service",
          "label": "corporate entertainment service"
        },
        {
          "code": "corporate_gift_supplier",
          "label": "corporate gift supplier"
        },
        {
          "code": "corporate_office",
          "label": "corporate office"
        },
        {
          "code": "correctional_services_department",
          "label": "correctional services department"
        },
        {
          "code": "cosmetic_dentist",
          "label": "cosmetic dentist"
        },
        {
          "code": "cosmetic_products_manufacturer",
          "label": "cosmetic products manufacturer"
        },
        {
          "code": "cosmetics_and_parfumes_supplier",
          "label": "cosmetics and perfumes supplier"
        },
        {
          "code": "cosmetics_industry",
          "label": "cosmetics industry"
        },
        {
          "code": "cosmetics_store",
          "label": "cosmetics store"
        },
        {
          "code": "cosmetics_wholesaler",
          "label": "cosmetics wholesaler"
        },
        {
          "code": "cosplay_cafe",
          "label": "cosplay cafe"
        },
        {
          "code": "costa_rican_restaurant",
          "label": "costa rican restaurant"
        },
        {
          "code": "costume_jewelry_shop",
          "label": "costume jewelry shop"
        },
        {
          "code": "costume_rental_service",
          "label": "costume rental service"
        },
        {
          "code": "costume_store",
          "label": "costume store"
        },
        {
          "code": "cottage",
          "label": "cottage"
        },
        {
          "code": "cottage_rental",
          "label": "cottage rental"
        },
        {
          "code": "cottage_village",
          "label": "cottage village"
        },
        {
          "code": "cotton_exporter",
          "label": "cotton exporter"
        },
        {
          "code": "cotton_mill",
          "label": "cotton mill"
        },
        {
          "code": "cotton_supplier",
          "label": "cotton supplier"
        },
        {
          "code": "council",
          "label": "council"
        },
        {
          "code": "counselor",
          "label": "counselor"
        },
        {
          "code": "countertop_store",
          "label": "countertop store"
        },
        {
          "code": "country_club",
          "label": "country club"
        },
        {
          "code": "country_food_restaurant",
          "label": "country food restaurant"
        },
        {
          "code": "country_house",
          "label": "country house"
        },
        {
          "code": "country_park",
          "label": "country park"
        },
        {
          "code": "county_government_office",
          "label": "county government office"
        },
        {
          "code": "courier_service",
          "label": "courier service"
        },
        {
          "code": "court_executive_officer",
          "label": "court executive officer"
        },
        {
          "code": "court_reporter",
          "label": "court reporter"
        },
        {
          "code": "couscous_restaurant",
          "label": "couscous restaurant"
        },
        {
          "code": "couture_store",
          "label": "couture store"
        },
        {
          "code": "coworking_space",
          "label": "coworking space"
        },
        {
          "code": "crab_dish_restaurant",
          "label": "crab house"
        },
        {
          "code": "craft_store",
          "label": "craft store"
        },
        {
          "code": "cramming_school",
          "label": "cramming school"
        },
        {
          "code": "crane_dealer",
          "label": "crane dealer"
        },
        {
          "code": "crane_rental_agency",
          "label": "crane rental agency"
        },
        {
          "code": "crane_service",
          "label": "crane service"
        },
        {
          "code": "craniosacral_therapy",
          "label": "craniosacral therapy"
        },
        {
          "code": "creche",
          "label": "creche"
        },
        {
          "code": "credit_counseling_service",
          "label": "credit counseling service"
        },
        {
          "code": "credit_reporting_agency",
          "label": "credit reporting agency"
        },
        {
          "code": "credit_union",
          "label": "credit union"
        },
        {
          "code": "cremation_service",
          "label": "cremation service"
        },
        {
          "code": "creole_restaurant",
          "label": "creole restaurant"
        },
        {
          "code": "creperie",
          "label": "cr�perie"
        },
        {
          "code": "cricket_club",
          "label": "cricket club"
        },
        {
          "code": "cricket_ground",
          "label": "cricket ground"
        },
        {
          "code": "cricket_shop",
          "label": "cricket shop"
        },
        {
          "code": "crime_victim_service",
          "label": "crime victim service"
        },
        {
          "code": "criminal_law_attorney",
          "label": "criminal justice attorney"
        },
        {
          "code": "croatian_restaurant",
          "label": "croatian restaurant"
        },
        {
          "code": "crop_grower",
          "label": "crop grower"
        },
        {
          "code": "croquet_club",
          "label": "croquet club"
        },
        {
          "code": "cruise_agency",
          "label": "cruise agency"
        },
        {
          "code": "cruise_line",
          "label": "cruise line company"
        },
        {
          "code": "cruise_terminal",
          "label": "cruise terminal"
        },
        {
          "code": "crushed_stone_supplier",
          "label": "crushed stone supplier"
        },
        {
          "code": "cuban_restaurant",
          "label": "cuban restaurant"
        },
        {
          "code": "culinary_school",
          "label": "culinary school"
        },
        {
          "code": "cultural_association",
          "label": "cultural association"
        },
        {
          "code": "cultural_center",
          "label": "cultural center"
        },
        {
          "code": "cupcake_shop",
          "label": "cupcake shop"
        },
        {
          "code": "cured_ham_bar",
          "label": "cured ham bar"
        },
        {
          "code": "cured_ham_store",
          "label": "cured ham store"
        },
        {
          "code": "cured_ham_warehouse",
          "label": "cured ham warehouse"
        },
        {
          "code": "curling_club",
          "label": "curling club"
        },
        {
          "code": "curling_hall",
          "label": "curling hall"
        },
        {
          "code": "currency_exchange_service",
          "label": "currency exchange service"
        },
        {
          "code": "curtain_and_upholstery_cleaner",
          "label": "curtain and upholstery cleaning service"
        },
        {
          "code": "curtain_store",
          "label": "curtain store"
        },
        {
          "code": "curtain_supplier_and_maker",
          "label": "curtain supplier and maker"
        },
        {
          "code": "custom_confiscated_goods_store",
          "label": "custom confiscated goods store"
        },
        {
          "code": "custom_home_builder",
          "label": "custom home builder"
        },
        {
          "code": "custom_label_printer",
          "label": "custom label printer"
        },
        {
          "code": "custom_t_shirt_store",
          "label": "custom t-shirt store"
        },
        {
          "code": "custom_tailor",
          "label": "custom tailor"
        },
        {
          "code": "customs_broker",
          "label": "customs broker"
        },
        {
          "code": "customs_consultant",
          "label": "customs consultant"
        },
        {
          "code": "customs_department",
          "label": "customs department"
        },
        {
          "code": "customs_office",
          "label": "customs office"
        },
        {
          "code": "customs_warehouse",
          "label": "customs warehouse"
        },
        {
          "code": "cutlery_store",
          "label": "cutlery store"
        },
        {
          "code": "cycling_park",
          "label": "cycling park"
        },
        {
          "code": "czech_restaurant",
          "label": "czech restaurant"
        },
        {
          "code": "dairy",
          "label": "dairy"
        },
        {
          "code": "dairy_farm",
          "label": "dairy farm"
        },
        {
          "code": "dairy_farm_equipment_supplier",
          "label": "dairy farm equipment supplier"
        },
        {
          "code": "dairy_store",
          "label": "dairy store"
        },
        {
          "code": "dairy_supplier",
          "label": "dairy supplier"
        },
        {
          "code": "dan_dan_noodle_restaurant",
          "label": "dan dan noodle restaurant"
        },
        {
          "code": "dance_club",
          "label": "dance club"
        },
        {
          "code": "dance_company",
          "label": "dance company"
        },
        {
          "code": "dance_conservatory",
          "label": "dance conservatory"
        },
        {
          "code": "dance_hall",
          "label": "dance hall"
        },
        {
          "code": "dance_pavillion",
          "label": "dance pavillion"
        },
        {
          "code": "dance_restaurant",
          "label": "dance restaurant"
        },
        {
          "code": "dance_school",
          "label": "dance school"
        },
        {
          "code": "dance_store",
          "label": "dance store"
        },
        {
          "code": "danish_restaurant",
          "label": "danish restaurant"
        },
        {
          "code": "dart_bar",
          "label": "dart bar"
        },
        {
          "code": "dart_supply_store",
          "label": "dart supply store"
        },
        {
          "code": "data_entry_service",
          "label": "data entry service"
        },
        {
          "code": "data_recovery_service",
          "label": "data recovery service"
        },
        {
          "code": "database_management_company",
          "label": "database management company"
        },
        {
          "code": "dating_service",
          "label": "dating service"
        },
        {
          "code": "day_care_center",
          "label": "day care center"
        },
        {
          "code": "day_spa",
          "label": "day spa"
        },
        {
          "code": "deaf_church",
          "label": "deaf church"
        },
        {
          "code": "deaf_school",
          "label": "deaf school"
        },
        {
          "code": "deaf_service",
          "label": "deaf service"
        },
        {
          "code": "debris_removal_service",
          "label": "debris removal service"
        },
        {
          "code": "debt_collecting",
          "label": "debt collecting"
        },
        {
          "code": "debt_collection_agency",
          "label": "debt collection agency"
        },
        {
          "code": "decal_supplier",
          "label": "decal supplier"
        },
        {
          "code": "deck_builder",
          "label": "deck builder"
        },
        {
          "code": "deli",
          "label": "deli"
        },
        {
          "code": "delivery_chinese_restaurant",
          "label": "delivery chinese restaurant"
        },
        {
          "code": "delivery_service",
          "label": "delivery service"
        },
        {
          "code": "demolition_contractor",
          "label": "demolition contractor"
        },
        {
          "code": "denim_wear_store",
          "label": "jeans shop"
        },
        {
          "code": "dental_clinic",
          "label": "dental clinic"
        },
        {
          "code": "dental_hygienist",
          "label": "dental hygienist"
        },
        {
          "code": "dental_implants_periodontist",
          "label": "dental implants periodontist"
        },
        {
          "code": "dental_insurance_agency",
          "label": "dental insurance agency"
        },
        {
          "code": "dental_lab",
          "label": "dental laboratory"
        },
        {
          "code": "dental_radiology",
          "label": "dental radiology"
        },
        {
          "code": "dental_school",
          "label": "dental school"
        },
        {
          "code": "dental_supply_store",
          "label": "dental supply store"
        },
        {
          "code": "dentist",
          "label": "dentist"
        },
        {
          "code": "denture_care_center",
          "label": "denture care center"
        },
        {
          "code": "department_for_regional_development",
          "label": "department for regional development"
        },
        {
          "code": "department_of_education",
          "label": "department of education"
        },
        {
          "code": "department_of_finance",
          "label": "department of finance"
        },
        {
          "code": "department_of_housing",
          "label": "department of housing"
        },
        {
          "code": "department_of_motor_vehicles",
          "label": "department of motor vehicles"
        },
        {
          "code": "department_of_public_safety",
          "label": "department of public safety"
        },
        {
          "code": "department_of_social_services",
          "label": "department of social services"
        },
        {
          "code": "department_of_transportation",
          "label": "department of transportation"
        },
        {
          "code": "department_store",
          "label": "department store"
        },
        {
          "code": "dept_of_city_treasure",
          "label": "dept of city treasure"
        },
        {
          "code": "dept_of_state_treasure",
          "label": "dept of state treasure"
        },
        {
          "code": "dermatologist",
          "label": "dermatologist"
        },
        {
          "code": "desalination_plant",
          "label": "desalination plant"
        },
        {
          "code": "design_agency",
          "label": "design agency"
        },
        {
          "code": "design_engineer",
          "label": "design engineer"
        },
        {
          "code": "design_institute",
          "label": "design institute"
        },
        {
          "code": "desktop_publishing_service",
          "label": "desktop publishing service"
        },
        {
          "code": "dessert_buffet",
          "label": "sweets and dessert buffet"
        },
        {
          "code": "dessert_restaurant",
          "label": "dessert restaurant"
        },
        {
          "code": "dessert_shop",
          "label": "dessert shop"
        },
        {
          "code": "detective",
          "label": "detective"
        },
        {
          "code": "detention_center",
          "label": "detention center"
        },
        {
          "code": "diabetes_center",
          "label": "diabetes center"
        },
        {
          "code": "diabetes_equipment_supplier",
          "label": "diabetes equipment supplier"
        },
        {
          "code": "diabetologist",
          "label": "diabetologist"
        },
        {
          "code": "diagnostic_center",
          "label": "diagnostic center"
        },
        {
          "code": "dialysis_center",
          "label": "dialysis center"
        },
        {
          "code": "diamond_buyer",
          "label": "diamond buyer"
        },
        {
          "code": "diamond_dealer",
          "label": "diamond dealer"
        },
        {
          "code": "diaper_service",
          "label": "diaper service"
        },
        {
          "code": "diesel_engine_dealer",
          "label": "diesel engine dealer"
        },
        {
          "code": "diesel_engine_repair_service",
          "label": "diesel engine repair service"
        },
        {
          "code": "diesel_fuel_supplier",
          "label": "diesel fuel supplier"
        },
        {
          "code": "digital_printer",
          "label": "digital printer"
        },
        {
          "code": "digital_printing_service",
          "label": "digital printing service"
        },
        {
          "code": "dim_sum_restaurant",
          "label": "dim sum restaurant"
        },
        {
          "code": "diner",
          "label": "diner"
        },
        {
          "code": "dinner_theater",
          "label": "dinner theater"
        },
        {
          "code": "direct_mail_advertising",
          "label": "direct mail advertising"
        },
        {
          "code": "dirt_supplier",
          "label": "dirt supplier"
        },
        {
          "code": "disability_equipment_supplier",
          "label": "disability equipment supplier"
        },
        {
          "code": "disability_services_and_support_organization",
          "label": "disability services & support organisation"
        },
        {
          "code": "disabled_sports_center",
          "label": "disabled sports center"
        },
        {
          "code": "disc_golf_course",
          "label": "disc golf course"
        },
        {
          "code": "disciples_of_christ_church",
          "label": "disciples of christ church"
        },
        {
          "code": "disco",
          "label": "disco club"
        },
        {
          "code": "discount_store",
          "label": "discount store"
        },
        {
          "code": "discount_supermarket",
          "label": "discount supermarket"
        },
        {
          "code": "display_home_center",
          "label": "display home centre"
        },
        {
          "code": "display_stand_manufacturer",
          "label": "display stand manufacturer"
        },
        {
          "code": "disposable_tableware_supplier",
          "label": "disposable tableware supplier"
        },
        {
          "code": "distance_learning_center",
          "label": "distance learning center"
        },
        {
          "code": "distillery",
          "label": "distillery"
        },
        {
          "code": "distribution_service",
          "label": "distribution service"
        },
        {
          "code": "district_attorney",
          "label": "district attorney"
        },
        {
          "code": "district_council",
          "label": "district council"
        },
        {
          "code": "district_government_office",
          "label": "district government office"
        },
        {
          "code": "district_justice",
          "label": "district justice"
        },
        {
          "code": "district_office",
          "label": "district office"
        },
        {
          "code": "dive_club",
          "label": "dive club"
        },
        {
          "code": "dive_shop",
          "label": "dive shop"
        },
        {
          "code": "diving_center",
          "label": "diving center"
        },
        {
          "code": "diving_service",
          "label": "diving contractor"
        },
        {
          "code": "divorce_attorney",
          "label": "divorce lawyer"
        },
        {
          "code": "divorce_service",
          "label": "divorce service"
        },
        {
          "code": "dj",
          "label": "dj service"
        },
        {
          "code": "dj_supply_store",
          "label": "dj supply store"
        },
        {
          "code": "do_it_yourself_store",
          "label": "do-it-yourself shop"
        },
        {
          "code": "dock_builder",
          "label": "dock builder"
        },
        {
          "code": "doctor",
          "label": "doctor"
        },
        {
          "code": "dodge_dealer",
          "label": "dodge dealer"
        },
        {
          "code": "dog_breeder",
          "label": "dog breeder"
        },
        {
          "code": "dog_cafe",
          "label": "dog cafe"
        },
        {
          "code": "dog_day_care_center",
          "label": "dog day care center"
        },
        {
          "code": "dog_hostel",
          "label": "dog hostel"
        },
        {
          "code": "dog_park",
          "label": "dog park"
        },
        {
          "code": "dog_trainer",
          "label": "dog trainer"
        },
        {
          "code": "dog_walker",
          "label": "dog walker"
        },
        {
          "code": "dogsled_ride_service",
          "label": "dogsled ride service"
        },
        {
          "code": "dojo_restaurant",
          "label": "dojo restaurant"
        },
        {
          "code": "doll_restoration_service",
          "label": "doll restoration service"
        },
        {
          "code": "doll_store",
          "label": "doll store"
        },
        {
          "code": "dollar_store",
          "label": "dollar store"
        },
        {
          "code": "domestic_abuse_treatment_center",
          "label": "domestic abuse treatment center"
        },
        {
          "code": "domestic_airport",
          "label": "domestic airport"
        },
        {
          "code": "dominican_restaurant",
          "label": "dominican restaurant"
        },
        {
          "code": "donations_center",
          "label": "donations center"
        },
        {
          "code": "donut_shop",
          "label": "donut shop"
        },
        {
          "code": "door_manufacturer",
          "label": "door manufacturer"
        },
        {
          "code": "door_shop",
          "label": "door shop"
        },
        {
          "code": "door_supplier",
          "label": "door supplier"
        },
        {
          "code": "door_warehouse",
          "label": "door warehouse"
        },
        {
          "code": "double_glazing_supplier",
          "label": "double glazing installer"
        },
        {
          "code": "down_home_cooking_restaurant",
          "label": "down home cooking restaurant"
        },
        {
          "code": "drafting_equipment_supplier",
          "label": "drafting equipment supplier"
        },
        {
          "code": "drafting_service",
          "label": "drafting service"
        },
        {
          "code": "drainage_service",
          "label": "drainage service"
        },
        {
          "code": "drama_school",
          "label": "drama school"
        },
        {
          "code": "drama_theater",
          "label": "drama theater"
        },
        {
          "code": "drawing_lessons",
          "label": "drawing lessons"
        },
        {
          "code": "dress_and_tuxedo_rental_service",
          "label": "dress and tuxedo rental service"
        },
        {
          "code": "dress_shop",
          "label": "dress store"
        },
        {
          "code": "dressmaker",
          "label": "dressmaker"
        },
        {
          "code": "dried_flower_shop",
          "label": "dried flower shop"
        },
        {
          "code": "dried_seafood_store",
          "label": "dried seafood store"
        },
        {
          "code": "drilling_contractor",
          "label": "drilling contractor"
        },
        {
          "code": "drilling_equipment_supplier",
          "label": "drilling equipment supplier"
        },
        {
          "code": "drinking_water_fountain",
          "label": "drinking water fountain"
        },
        {
          "code": "drive_in_movie_theater",
          "label": "drive-in movie theater"
        },
        {
          "code": "driver_vehicle_licensing_agency",
          "label": "driver and vehicle licensing agency"
        },
        {
          "code": "drivers_license_office",
          "label": "driver's license office"
        },
        {
          "code": "drivers_license_training_school",
          "label": "drivers license training school"
        },
        {
          "code": "driveshaft_shop",
          "label": "driveshaft shop"
        },
        {
          "code": "driving_school",
          "label": "driving school"
        },
        {
          "code": "driving_test_centre",
          "label": "driving test centre"
        },
        {
          "code": "drug_testing_service",
          "label": "drug testing service"
        },
        {
          "code": "drugstore",
          "label": "drug store"
        },
        {
          "code": "drum_school",
          "label": "drum school"
        },
        {
          "code": "drum_store",
          "label": "drum store"
        },
        {
          "code": "dry_cleaner",
          "label": "dry cleaner"
        },
        {
          "code": "dry_fruit_store",
          "label": "dry fruit store"
        },
        {
          "code": "dry_ice_supplier",
          "label": "dry ice supplier"
        },
        {
          "code": "dry_wall_contractor",
          "label": "dry wall contractor"
        },
        {
          "code": "dry_wall_supply_store",
          "label": "dry wall supply store"
        },
        {
          "code": "ducati_dealer",
          "label": "ducati dealer"
        },
        {
          "code": "dude_ranch",
          "label": "dude ranch"
        },
        {
          "code": "dump_truck_dealer",
          "label": "dump truck dealer"
        },
        {
          "code": "dumpling_restaurant",
          "label": "dumpling restaurant"
        },
        {
          "code": "dutch_restaurant",
          "label": "dutch restaurant"
        },
        {
          "code": "duty_free_store",
          "label": "duty free store"
        },
        {
          "code": "dvd_store",
          "label": "dvd store"
        },
        {
          "code": "dye_store",
          "label": "dye store"
        },
        {
          "code": "dyeworks",
          "label": "dyeworks"
        },
        {
          "code": "dynamometer_supplier",
          "label": "dynamometer supplier"
        },
        {
          "code": "e_commerce_agency",
          "label": "e commerce agency"
        },
        {
          "code": "e_commerce_service",
          "label": "e-commerce service"
        },
        {
          "code": "ear_piercing_service",
          "label": "ear piercing service"
        },
        {
          "code": "earth_works_company",
          "label": "earth works company"
        },
        {
          "code": "east_african_restaurant",
          "label": "east african restaurant"
        },
        {
          "code": "east_javanese_restaurant",
          "label": "east javanese restaurant"
        },
        {
          "code": "eastern_european_restaurant",
          "label": "eastern european restaurant"
        },
        {
          "code": "eastern_orthodox_church",
          "label": "eastern orthodox church"
        },
        {
          "code": "eating_disorder_treatment_center",
          "label": "eating disorder treatment center"
        },
        {
          "code": "eclectic_restaurant",
          "label": "eclectic restaurant"
        },
        {
          "code": "ecological_park",
          "label": "ecological park"
        },
        {
          "code": "ecologists_association",
          "label": "ecologists association"
        },
        {
          "code": "economic_consultant",
          "label": "economic consultant"
        },
        {
          "code": "economic_development_agency",
          "label": "economic development agency"
        },
        {
          "code": "ecuadorian_restaurant",
          "label": "ecuadorian restaurant"
        },
        {
          "code": "education_center",
          "label": "education center"
        },
        {
          "code": "educational_consultant",
          "label": "educational consultant"
        },
        {
          "code": "educational_institution",
          "label": "educational institution"
        },
        {
          "code": "educational_supply_store",
          "label": "educational supply store"
        },
        {
          "code": "educational_testing_service",
          "label": "educational testing service"
        },
        {
          "code": "eftpos_equipment_supplier",
          "label": "eftpos equipment supplier"
        },
        {
          "code": "egg_supplier",
          "label": "egg supplier"
        },
        {
          "code": "egyptian_restaurant",
          "label": "egyptian restaurant"
        },
        {
          "code": "elder_law_attorney",
          "label": "elder law attorney"
        },
        {
          "code": "electric_motor_repair_shop",
          "label": "electric motor repair shop"
        },
        {
          "code": "electric_motor_store",
          "label": "electric motor store"
        },
        {
          "code": "electric_utility_company",
          "label": "electric utility company"
        },
        {
          "code": "electric_utility_manufacturer",
          "label": "electric utility manufacturer"
        },
        {
          "code": "electric_vehicle_charging_station",
          "label": "electric vehicle charging station"
        },
        {
          "code": "electrical_appliance_wholesaler",
          "label": "electrical appliance wholesaler"
        },
        {
          "code": "electrical_engineer",
          "label": "electrical engineer"
        },
        {
          "code": "electrical_equipment_supplier",
          "label": "electrical equipment supplier"
        },
        {
          "code": "electrical_installation_service",
          "label": "electrical installation service"
        },
        {
          "code": "electrical_repair_shop",
          "label": "electrical repair shop"
        },
        {
          "code": "electrical_substation",
          "label": "electrical substation"
        },
        {
          "code": "electrical_supply_store",
          "label": "electrical supply store"
        },
        {
          "code": "electrical_wholesaler",
          "label": "electrical wholesaler"
        },
        {
          "code": "electrician",
          "label": "electrician"
        },
        {
          "code": "electrolysis_hair_removal_service",
          "label": "electrolysis hair removal service"
        },
        {
          "code": "electronic_engineer",
          "label": "electronic engineer"
        },
        {
          "code": "electronic_parts_supplier",
          "label": "electronic parts supplier"
        },
        {
          "code": "electronics_accessories_wholesaler",
          "label": "electronics accessories wholesaler"
        },
        {
          "code": "electronics_company",
          "label": "electronics company"
        },
        {
          "code": "electronics_engineer",
          "label": "electronics engineer"
        },
        {
          "code": "electronics_exporter",
          "label": "electronics exporter"
        },
        {
          "code": "electronics_hire_shop",
          "label": "electronics hire shop"
        },
        {
          "code": "electronics_manufacturer",
          "label": "electronics manufacturer"
        },
        {
          "code": "electronics_repair_shop",
          "label": "electronics repair shop"
        },
        {
          "code": "electronics_store",
          "label": "electronics store"
        },
        {
          "code": "electronics_vending_machine",
          "label": "electronics vending machine"
        },
        {
          "code": "electronics_wholesaler",
          "label": "electronics wholesaler"
        },
        {
          "code": "elementary_school",
          "label": "elementary school"
        },
        {
          "code": "elevator_manufacturer",
          "label": "elevator manufacturer"
        },
        {
          "code": "elevator_service",
          "label": "elevator service"
        },
        {
          "code": "embassy",
          "label": "embassy"
        },
        {
          "code": "embossing_service",
          "label": "embossing service"
        },
        {
          "code": "embroidery_service",
          "label": "embroidery service"
        },
        {
          "code": "embroidery_shop",
          "label": "embroidery shop"
        },
        {
          "code": "emergency_call_station",
          "label": "emergency call booth"
        },
        {
          "code": "emergency_care_physician",
          "label": "emergency care physician"
        },
        {
          "code": "emergency_care_service",
          "label": "emergency care service"
        },
        {
          "code": "emergency_dental_service",
          "label": "emergency dental service"
        },
        {
          "code": "emergency_locksmith_service",
          "label": "emergency locksmith service"
        },
        {
          "code": "emergency_management_ministry",
          "label": "emergency management ministry"
        },
        {
          "code": "emergency_room",
          "label": "emergency room"
        },
        {
          "code": "emergency_training",
          "label": "emergency training"
        },
        {
          "code": "emergency_training_school",
          "label": "emergency training school"
        },
        {
          "code": "emergency_veterinarian_service",
          "label": "emergency veterinarian service"
        },
        {
          "code": "employment_agency",
          "label": "employment agency"
        },
        {
          "code": "employment_attorney",
          "label": "employment attorney"
        },
        {
          "code": "employment_center",
          "label": "employment center"
        },
        {
          "code": "employment_consultant",
          "label": "employment consultant"
        },
        {
          "code": "employment_search_service",
          "label": "employment search service"
        },
        {
          "code": "endocrinologist",
          "label": "endocrinologist"
        },
        {
          "code": "endodontist",
          "label": "endodontist"
        },
        {
          "code": "endoscopist",
          "label": "endoscopist"
        },
        {
          "code": "energy_equipment_and_solutions",
          "label": "energy equipment and solutions"
        },
        {
          "code": "energy_supplier",
          "label": "energy supplier"
        },
        {
          "code": "engine_rebuilding_service",
          "label": "engine rebuilding service"
        },
        {
          "code": "engineer",
          "label": "engineer"
        },
        {
          "code": "engineering_consultant",
          "label": "engineering consultant"
        },
        {
          "code": "engineering_school",
          "label": "engineering school"
        },
        {
          "code": "english_language_camp",
          "label": "english language camp"
        },
        {
          "code": "english_language_instructor",
          "label": "english language instructor"
        },
        {
          "code": "english_language_school",
          "label": "english language school"
        },
        {
          "code": "english_restaurant",
          "label": "english restaurant"
        },
        {
          "code": "engraver",
          "label": "engraver"
        },
        {
          "code": "entertainer",
          "label": "entertainer"
        },
        {
          "code": "entertainment_agency",
          "label": "entertainment agency"
        },
        {
          "code": "envelope_supplier",
          "label": "envelope supplier"
        },
        {
          "code": "environment_office",
          "label": "environment office"
        },
        {
          "code": "environment_renewable_natural_resources",
          "label": "environment renewable natural resources"
        },
        {
          "code": "environmental_consultant",
          "label": "environmental consultant"
        },
        {
          "code": "environmental_engineer",
          "label": "environmental engineer"
        },
        {
          "code": "environmental_health_service",
          "label": "environmental health service"
        },
        {
          "code": "environmental_organization",
          "label": "environmental organization"
        },
        {
          "code": "environmental_protection_organization",
          "label": "environmental protection organization"
        },
        {
          "code": "episcopal_church",
          "label": "episcopal church"
        },
        {
          "code": "equestrian_club",
          "label": "equestrian club"
        },
        {
          "code": "equestrian_facility",
          "label": "equestrian facility"
        },
        {
          "code": "equestrian_store",
          "label": "equestrian store"
        },
        {
          "code": "equipment_exporter",
          "label": "equipment exporter"
        },
        {
          "code": "equipment_importer",
          "label": "equipment importer"
        },
        {
          "code": "equipment_rental_agency",
          "label": "equipment rental agency"
        },
        {
          "code": "equipment_supplier",
          "label": "equipment supplier"
        },
        {
          "code": "eritrean_restaurant",
          "label": "eritrean restaurant"
        },
        {
          "code": "erotic_massage",
          "label": "erotic massage"
        },
        {
          "code": "escape_room_center",
          "label": "escape room center"
        },
        {
          "code": "escrow_service",
          "label": "escrow service"
        },
        {
          "code": "espresso_bar",
          "label": "espresso bar"
        },
        {
          "code": "estate_appraiser",
          "label": "estate appraiser"
        },
        {
          "code": "estate_liquidator",
          "label": "estate liquidator"
        },
        {
          "code": "estate_planning_attorney",
          "label": "estate planning attorney"
        },
        {
          "code": "ethiopian_restaurant",
          "label": "ethiopian restaurant"
        },
        {
          "code": "ethnic_restaurant",
          "label": "ethnic restaurant"
        },
        {
          "code": "ethnographic_museum",
          "label": "ethnographic museum"
        },
        {
          "code": "european_institution",
          "label": "european institution"
        },
        {
          "code": "european_restaurant",
          "label": "european restaurant"
        },
        {
          "code": "evangelical_church",
          "label": "evangelical church"
        },
        {
          "code": "evening_dress_rental_service",
          "label": "evening dress rental service"
        },
        {
          "code": "evening_school",
          "label": "evening school"
        },
        {
          "code": "event_management_company",
          "label": "event management company"
        },
        {
          "code": "event_planner",
          "label": "event planner"
        },
        {
          "code": "event_technology_service",
          "label": "event technology service"
        },
        {
          "code": "event_ticket_seller",
          "label": "event ticket seller"
        },
        {
          "code": "event_venue",
          "label": "event venue"
        },
        {
          "code": "excavating_contractor",
          "label": "excavating contractor"
        },
        {
          "code": "executive_search_firm",
          "label": "executive search firm"
        },
        {
          "code": "executive_suite_rental_agency",
          "label": "executive suite rental agency"
        },
        {
          "code": "executor",
          "label": "executor"
        },
        {
          "code": "exhibit",
          "label": "exhibit"
        },
        {
          "code": "exhibition_and_trade_center",
          "label": "exhibition and trade centre"
        },
        {
          "code": "exhibition_planner",
          "label": "exhibition planner"
        },
        {
          "code": "exporter",
          "label": "exporter"
        },
        {
          "code": "extended_stay_hotel",
          "label": "extended stay hotel"
        },
        {
          "code": "extremadurian_restaurant",
          "label": "extremadurian restaurant"
        },
        {
          "code": "eye_care_center",
          "label": "eye care center"
        },
        {
          "code": "eyebrow_bar",
          "label": "eyebrow bar"
        },
        {
          "code": "fabric_product_manufacturer",
          "label": "fabric product manufacturer"
        },
        {
          "code": "fabric_store",
          "label": "fabric store"
        },
        {
          "code": "fabric_wholesaler",
          "label": "fabric wholesaler"
        },
        {
          "code": "fabrication_engineer",
          "label": "fabrication engineer"
        },
        {
          "code": "facial_spa",
          "label": "facial spa"
        },
        {
          "code": "factory_equipment_supplier",
          "label": "factory equipment supplier"
        },
        {
          "code": "faculty_of_arts",
          "label": "faculty of arts"
        },
        {
          "code": "faculty_of_law",
          "label": "faculty of law"
        },
        {
          "code": "faculty_of_pharmacy",
          "label": "faculty of pharmacy"
        },
        {
          "code": "faculty_of_psychology",
          "label": "faculty of psychology"
        },
        {
          "code": "faculty_of_science",
          "label": "faculty of science"
        },
        {
          "code": "faculty_of_sports",
          "label": "faculty of sports"
        },
        {
          "code": "fair_trade_organization",
          "label": "fair trade organization"
        },
        {
          "code": "fairground",
          "label": "fairground"
        },
        {
          "code": "falafel_restaurant",
          "label": "falafel restaurant"
        },
        {
          "code": "family_counselor",
          "label": "family counselor"
        },
        {
          "code": "family_day_care_service",
          "label": "family day care service"
        },
        {
          "code": "family_law_attorney",
          "label": "family law attorney"
        },
        {
          "code": "family_planning_center",
          "label": "family planning center"
        },
        {
          "code": "family_planning_counselor",
          "label": "family planning counselor"
        },
        {
          "code": "family_practice_physician",
          "label": "family practice physician"
        },
        {
          "code": "family_restaurant",
          "label": "family restaurant"
        },
        {
          "code": "family_service_center",
          "label": "family service center"
        },
        {
          "code": "farm",
          "label": "farm"
        },
        {
          "code": "farm_bureau",
          "label": "farm bureau"
        },
        {
          "code": "farm_equipment_repair_service",
          "label": "farm equipment repair service"
        },
        {
          "code": "farm_equipment_supplier",
          "label": "farm equipment supplier"
        },
        {
          "code": "farm_household_tour",
          "label": "farm household tour"
        },
        {
          "code": "farm_school",
          "label": "farm school"
        },
        {
          "code": "farm_shop",
          "label": "farm shop"
        },
        {
          "code": "farmers_market",
          "label": "farmers' market"
        },
        {
          "code": "farmstay",
          "label": "farmstay"
        },
        {
          "code": "fashion_accessories_store",
          "label": "fashion accessories store"
        },
        {
          "code": "fashion_design_school",
          "label": "fashion design school"
        },
        {
          "code": "fashion_designer",
          "label": "fashion designer"
        },
        {
          "code": "fast_food_restaurant",
          "label": "fast food restaurant"
        },
        {
          "code": "fastener_supplier",
          "label": "fastener supplier"
        },
        {
          "code": "favela",
          "label": "favela"
        },
        {
          "code": "fax_service",
          "label": "fax service"
        },
        {
          "code": "federal_agency_for_technical_relief",
          "label": "federal agency for technical relief"
        },
        {
          "code": "federal_credit_union",
          "label": "federal credit union"
        },
        {
          "code": "federal_government_office",
          "label": "federal government office"
        },
        {
          "code": "federal_police",
          "label": "federal police"
        },
        {
          "code": "federal_reserve_bank",
          "label": "federal reserve bank"
        },
        {
          "code": "feed_manufacturer",
          "label": "feed manufacturer"
        },
        {
          "code": "feed_store",
          "label": "animal feed store"
        },
        {
          "code": "felt_boots_store",
          "label": "felt boots store"
        },
        {
          "code": "fence_contractor",
          "label": "fence contractor"
        },
        {
          "code": "fence_supply_store",
          "label": "fence supply store"
        },
        {
          "code": "fencing_salon",
          "label": "fencing salon"
        },
        {
          "code": "fencing_school",
          "label": "fencing school"
        },
        {
          "code": "feng_shui_consultant",
          "label": "feng shui consultant"
        },
        {
          "code": "feng_shui_shop",
          "label": "feng shui shop"
        },
        {
          "code": "ferrari_dealer",
          "label": "ferrari dealer"
        },
        {
          "code": "ferris_wheel",
          "label": "ferris wheel"
        },
        {
          "code": "ferry_service",
          "label": "ferry service"
        },
        {
          "code": "fertility_clinic",
          "label": "fertility clinic"
        },
        {
          "code": "fertility_physician",
          "label": "fertility physician"
        },
        {
          "code": "fertilizer_supplier",
          "label": "fertilizer supplier"
        },
        {
          "code": "festival",
          "label": "festival"
        },
        {
          "code": "festival_hall",
          "label": "festival hall"
        },
        {
          "code": "fiat_dealer",
          "label": "fiat dealer"
        },
        {
          "code": "fiber_optic_products_supplier",
          "label": "fiber optic products supplier"
        },
        {
          "code": "fiberglass_repair_service",
          "label": "fiberglass repair service"
        },
        {
          "code": "fiberglass_supplier",
          "label": "fiberglass supplier"
        },
        {
          "code": "figurine_shop",
          "label": "figurine shop"
        },
        {
          "code": "filipino_restaurant",
          "label": "filipino restaurant"
        },
        {
          "code": "film_and_photograph_library",
          "label": "film and photograph library"
        },
        {
          "code": "film_production_company",
          "label": "film production company"
        },
        {
          "code": "filtration_plant",
          "label": "filtration plant"
        },
        {
          "code": "finance_broker",
          "label": "finance broker"
        },
        {
          "code": "financial_audit",
          "label": "financial audit"
        },
        {
          "code": "financial_consultant",
          "label": "financial consultant"
        },
        {
          "code": "financial_institution",
          "label": "financial institution"
        },
        {
          "code": "financial_planner",
          "label": "financial planner"
        },
        {
          "code": "fine_dining_restaurant",
          "label": "fine dining restaurant"
        },
        {
          "code": "fingerprinting_service",
          "label": "fingerprinting service"
        },
        {
          "code": "finishing_materials_supplier",
          "label": "finishing materials supplier"
        },
        {
          "code": "finnish_restaurant",
          "label": "finnish restaurant"
        },
        {
          "code": "fire_alarm_supplier",
          "label": "fire alarm supplier"
        },
        {
          "code": "fire_damage_restoration_service",
          "label": "fire damage restoration service"
        },
        {
          "code": "fire_department_equipment_supplier",
          "label": "fire department equipment supplier"
        },
        {
          "code": "fire_fighters_academy",
          "label": "fire fighters academy"
        },
        {
          "code": "fire_protection_consultant",
          "label": "fire protection consultant"
        },
        {
          "code": "fire_protection_equipment_supplier",
          "label": "fire protection equipment supplier"
        },
        {
          "code": "fire_protection_service",
          "label": "fire protection service"
        },
        {
          "code": "fire_protection_system_supplier",
          "label": "fire protection system supplier"
        },
        {
          "code": "fire_station",
          "label": "fire station"
        },
        {
          "code": "firearms_academy",
          "label": "firearms academy"
        },
        {
          "code": "fireplace_manufacturer",
          "label": "fireplace manufacturer"
        },
        {
          "code": "fireplace_store",
          "label": "fireplace store"
        },
        {
          "code": "firewood_supplier",
          "label": "firewood supplier"
        },
        {
          "code": "fireworks_store",
          "label": "fireworks store"
        },
        {
          "code": "fireworks_supplier",
          "label": "fireworks supplier"
        },
        {
          "code": "first_aid",
          "label": "first aid station"
        },
        {
          "code": "fish_and_chips_restaurant",
          "label": "fish & chips restaurant"
        },
        {
          "code": "fish_and_chips_takeaway",
          "label": "fish and chips takeaway"
        },
        {
          "code": "fish_farm",
          "label": "fish farm"
        },
        {
          "code": "fish_processing",
          "label": "fish processing"
        },
        {
          "code": "fish_spa",
          "label": "fish spa"
        },
        {
          "code": "fish_store",
          "label": "fish store"
        },
        {
          "code": "fishing_camp",
          "label": "fishing camp"
        },
        {
          "code": "fishing_charter",
          "label": "fishing charter"
        },
        {
          "code": "fishing_club",
          "label": "fishing club"
        },
        {
          "code": "fishing_pier",
          "label": "fishing pier"
        },
        {
          "code": "fishing_pond",
          "label": "fishing pond"
        },
        {
          "code": "fishing_store",
          "label": "fishing store"
        },
        {
          "code": "fitness_center",
          "label": "fitness center"
        },
        {
          "code": "fitness_equipment_store",
          "label": "exercise equipment store"
        },
        {
          "code": "fitness_equipment_wholesaler",
          "label": "fitness equipment wholesaler"
        },
        {
          "code": "fitted_furniture_supplier",
          "label": "fitted furniture supplier"
        },
        {
          "code": "flag_store",
          "label": "flag store"
        },
        {
          "code": "flamenco_dance_store",
          "label": "flamenco dance store"
        },
        {
          "code": "flamenco_school",
          "label": "flamenco school"
        },
        {
          "code": "flamenco_theater",
          "label": "flamenco theater"
        },
        {
          "code": "flavours_fragrances_and_aroma_supplier",
          "label": "flavours fragrances and aroma supplier"
        },
        {
          "code": "flea_market",
          "label": "flea market"
        },
        {
          "code": "flight_school",
          "label": "flight school"
        },
        {
          "code": "floating_market",
          "label": "floating market"
        },
        {
          "code": "floor_refinishing_service",
          "label": "floor refinishing service"
        },
        {
          "code": "floor_sanding_and_polishing_service",
          "label": "floor sanding and polishing service"
        },
        {
          "code": "flooring_contractor",
          "label": "flooring contractor"
        },
        {
          "code": "flooring_store",
          "label": "flooring store"
        },
        {
          "code": "floridian_restaurant",
          "label": "floridian restaurant"
        },
        {
          "code": "florist",
          "label": "florist"
        },
        {
          "code": "flour_mill",
          "label": "flour mill"
        },
        {
          "code": "flower_delivery",
          "label": "flower delivery"
        },
        {
          "code": "flower_designer",
          "label": "flower designer"
        },
        {
          "code": "flower_market",
          "label": "flower market"
        },
        {
          "code": "fmcg_goods_wholesaler",
          "label": "fmcg goods wholesaler"
        },
        {
          "code": "fmcg_manufacturer",
          "label": "fmcg manufacturer"
        },
        {
          "code": "foam_rubber_producer",
          "label": "foam rubber producer"
        },
        {
          "code": "foam_rubber_supplier",
          "label": "foam rubber supplier"
        },
        {
          "code": "folk_high_school",
          "label": "folk high school"
        },
        {
          "code": "fondue_restaurant",
          "label": "fondue restaurant"
        },
        {
          "code": "food_and_beverage_consultant",
          "label": "food and beverage consultant"
        },
        {
          "code": "food_and_beverage_exporter",
          "label": "food and beverage exporter"
        },
        {
          "code": "food_bank",
          "label": "food bank"
        },
        {
          "code": "food_broker",
          "label": "food broker"
        },
        {
          "code": "food_court",
          "label": "food court"
        },
        {
          "code": "food_machinery_supplier",
          "label": "food machinery supplier"
        },
        {
          "code": "food_manufacturer",
          "label": "food manufacturer"
        },
        {
          "code": "food_manufacturing_supply",
          "label": "food manufacturing supply"
        },
        {
          "code": "food_processing_company",
          "label": "food processing company"
        },
        {
          "code": "food_processing_equipment",
          "label": "food processing equipment"
        },
        {
          "code": "food_producer",
          "label": "food producer"
        },
        {
          "code": "food_products_supplier",
          "label": "food products supplier"
        },
        {
          "code": "food_seasoning_manufacturer",
          "label": "food seasoning manufacturer"
        },
        {
          "code": "foot_bath",
          "label": "foot bath"
        },
        {
          "code": "foot_care",
          "label": "foot care"
        },
        {
          "code": "foot_massage_parlor",
          "label": "foot massage parlor"
        },
        {
          "code": "football_club",
          "label": "football club"
        },
        {
          "code": "football_field",
          "label": "american football field"
        },
        {
          "code": "ford_dealer",
          "label": "ford dealer"
        },
        {
          "code": "foreclosure_service",
          "label": "foreclosure service"
        },
        {
          "code": "foreign_consulate",
          "label": "foreign consulate"
        },
        {
          "code": "foreign_exchange_students_organization",
          "label": "foreign exchange students organization"
        },
        {
          "code": "foreign_languages_program_school",
          "label": "foreign languages program school"
        },
        {
          "code": "foreign_trade_consultant",
          "label": "foreign trade consultant"
        },
        {
          "code": "foreman_builders_association",
          "label": "foreman builders association"
        },
        {
          "code": "forensic_consultant",
          "label": "forensic consultant"
        },
        {
          "code": "forestry_service",
          "label": "forestry service"
        },
        {
          "code": "forklift_dealer",
          "label": "forklift dealer"
        },
        {
          "code": "forklift_rental_service",
          "label": "forklift rental service"
        },
        {
          "code": "formal_clothing_store",
          "label": "formal wear store"
        },
        {
          "code": "fortress",
          "label": "fortress"
        },
        {
          "code": "fortune_telling_services",
          "label": "fortune telling services"
        },
        {
          "code": "foster_care_service",
          "label": "foster care service"
        },
        {
          "code": "foundation",
          "label": "foundation"
        },
        {
          "code": "foundry",
          "label": "foundry"
        },
        {
          "code": "fountain_contractor",
          "label": "fountain contractor"
        },
        {
          "code": "foursquare_church",
          "label": "foursquare church"
        },
        {
          "code": "fraternal_organization",
          "label": "fraternal organization"
        },
        {
          "code": "free_clinic",
          "label": "free clinic"
        },
        {
          "code": "free_parking_lot",
          "label": "free parking lot"
        },
        {
          "code": "freestyle_wrestling",
          "label": "freestyle wrestling"
        },
        {
          "code": "freight_forwarding_service",
          "label": "freight forwarding service"
        },
        {
          "code": "french_language_school",
          "label": "french language school"
        },
        {
          "code": "french_restaurant",
          "label": "french restaurant"
        },
        {
          "code": "french_steakhouse_restaurant",
          "label": "french steakhouse restaurant"
        },
        {
          "code": "fresh_food_market",
          "label": "fresh food market"
        },
        {
          "code": "fried_chicken_takeaway",
          "label": "fried chicken takeaway"
        },
        {
          "code": "friends_church",
          "label": "friends church"
        },
        {
          "code": "frituur",
          "label": "frituur"
        },
        {
          "code": "frozen_dessert_supplier",
          "label": "frozen dessert supplier"
        },
        {
          "code": "frozen_food_manufacturer",
          "label": "frozen food manufacturer"
        },
        {
          "code": "frozen_food_store",
          "label": "frozen food store"
        },
        {
          "code": "frozen_yogurt_shop",
          "label": "frozen yogurt shop"
        },
        {
          "code": "fruit_and_vegetable_processing",
          "label": "fruit and vegetable processing"
        },
        {
          "code": "fruit_and_vegetable_store",
          "label": "fruit and vegetable store"
        },
        {
          "code": "fruit_and_vegetable_wholesaler",
          "label": "fruit and vegetable wholesaler"
        },
        {
          "code": "fruit_parlor",
          "label": "fruit parlor"
        },
        {
          "code": "fruit_wholesaler",
          "label": "fruit wholesaler"
        },
        {
          "code": "fruits_wholesaler",
          "label": "fruits wholesaler"
        },
        {
          "code": "fu_jian_restaurant",
          "label": "fujian restaurant"
        },
        {
          "code": "fuel_supplier",
          "label": "fuel supplier"
        },
        {
          "code": "fugu_restaurant",
          "label": "fugu restaurant"
        },
        {
          "code": "full_dress_rental_service",
          "label": "full dress rental service"
        },
        {
          "code": "full_gospel_church",
          "label": "full gospel church"
        },
        {
          "code": "function_room_facility",
          "label": "function room facility"
        },
        {
          "code": "fund_management_company",
          "label": "fund management company"
        },
        {
          "code": "funeral_director",
          "label": "funeral director"
        },
        {
          "code": "funeral_home",
          "label": "funeral home"
        },
        {
          "code": "fur_coat_shop",
          "label": "fur coat shop"
        },
        {
          "code": "fur_manufacturer",
          "label": "fur manufacturer"
        },
        {
          "code": "fur_service",
          "label": "fur service"
        },
        {
          "code": "furnace_parts_supplier",
          "label": "furnace parts supplier"
        },
        {
          "code": "furnace_repair_service",
          "label": "furnace repair service"
        },
        {
          "code": "furnace_store",
          "label": "furnace store"
        },
        {
          "code": "furnished_apartment_building",
          "label": "furnished apartment building"
        },
        {
          "code": "furniture_accessories",
          "label": "furniture accessories"
        },
        {
          "code": "furniture_accessories_supplier",
          "label": "furniture accessories supplier"
        },
        {
          "code": "furniture_maker",
          "label": "furniture maker"
        },
        {
          "code": "furniture_manufacturer",
          "label": "furniture manufacturer"
        },
        {
          "code": "furniture_rental_service",
          "label": "furniture rental service"
        },
        {
          "code": "furniture_repair_shop",
          "label": "furniture repair shop"
        },
        {
          "code": "furniture_store",
          "label": "furniture store"
        },
        {
          "code": "furniture_wholesaler",
          "label": "furniture wholesaler"
        },
        {
          "code": "fusion_restaurant",
          "label": "fusion restaurant"
        },
        {
          "code": "futon_store",
          "label": "futon store"
        },
        {
          "code": "futsal_field",
          "label": "futsal court"
        },
        {
          "code": "galician_restaurant",
          "label": "galician restaurant"
        },
        {
          "code": "gambling_house",
          "label": "gambling house"
        },
        {
          "code": "gambling_instructor",
          "label": "gambling instructor"
        },
        {
          "code": "game_store",
          "label": "game store"
        },
        {
          "code": "garage_builder",
          "label": "garage builder"
        },
        {
          "code": "garage_door_supplier",
          "label": "garage door supplier"
        },
        {
          "code": "garbage_collection_service",
          "label": "garbage collection service"
        },
        {
          "code": "garbage_dump",
          "label": "garbage dump"
        },
        {
          "code": "garbage_dump_service",
          "label": "garbage dump service"
        },
        {
          "code": "garden",
          "label": "garden"
        },
        {
          "code": "garden_building_retail",
          "label": "garden building supplier"
        },
        {
          "code": "garden_center",
          "label": "garden center"
        },
        {
          "code": "garden_furniture_store",
          "label": "garden furniture shop"
        },
        {
          "code": "gardener",
          "label": "gardener"
        },
        {
          "code": "garment_exporter",
          "label": "garment exporter"
        },
        {
          "code": "gas_company",
          "label": "gas company"
        },
        {
          "code": "gas_cylinders_supplier",
          "label": "gas cylinders supplier"
        },
        {
          "code": "gas_engineer",
          "label": "gas engineer"
        },
        {
          "code": "gas_installation_service",
          "label": "gas installation service"
        },
        {
          "code": "gas_logs_supplier",
          "label": "gas logs supplier"
        },
        {
          "code": "gas_shop",
          "label": "gas shop"
        },
        {
          "code": "gas_station",
          "label": "gas station"
        },
        {
          "code": "gasfitter",
          "label": "gasfitter"
        },
        {
          "code": "gasket_manufacturer",
          "label": "gasket manufacturer"
        },
        {
          "code": "gastroenterologist",
          "label": "gastroenterologist"
        },
        {
          "code": "gastrointestinal_surgeon",
          "label": "gastrointestinal surgeon"
        },
        {
          "code": "gastropub",
          "label": "gastropub"
        },
        {
          "code": "gay_and_lesbian_organization",
          "label": "gay & lesbian organization"
        },
        {
          "code": "gay_bar",
          "label": "gay bar"
        },
        {
          "code": "gay_night_club",
          "label": "gay night club"
        },
        {
          "code": "gay_sauna",
          "label": "gay sauna"
        },
        {
          "code": "gazebo_builder",
          "label": "gazebo builder"
        },
        {
          "code": "gemologist",
          "label": "gemologist"
        },
        {
          "code": "genealogist",
          "label": "genealogist"
        },
        {
          "code": "general_contractor",
          "label": "general contractor"
        },
        {
          "code": "general_hospital",
          "label": "general hospital"
        },
        {
          "code": "general_practice_attorney",
          "label": "general practice attorney"
        },
        {
          "code": "general_practitioner",
          "label": "general practitioner"
        },
        {
          "code": "general_register_office",
          "label": "general register office"
        },
        {
          "code": "general_store",
          "label": "general store"
        },
        {
          "code": "generator_shop",
          "label": "generator shop"
        },
        {
          "code": "genesis_dealer",
          "label": "genesis dealer"
        },
        {
          "code": "geography_and_history_faculty",
          "label": "geography and history faculty"
        },
        {
          "code": "geological_research_company",
          "label": "geological research company"
        },
        {
          "code": "geological_service",
          "label": "geological service"
        },
        {
          "code": "geologist",
          "label": "geologist"
        },
        {
          "code": "georgian_restaurant",
          "label": "georgian restaurant"
        },
        {
          "code": "geotechnical_engineer",
          "label": "geotechnical engineer"
        },
        {
          "code": "german_language_school",
          "label": "german language school"
        },
        {
          "code": "german_restaurant",
          "label": "german restaurant"
        },
        {
          "code": "ghost_town",
          "label": "ghost town"
        },
        {
          "code": "gift_basket_store",
          "label": "gift basket store"
        },
        {
          "code": "gift_shop",
          "label": "gift shop"
        },
        {
          "code": "gift_wrap_store",
          "label": "gift wrap store"
        },
        {
          "code": "girl_bar",
          "label": "girl bar"
        },
        {
          "code": "girls_secondary_school",
          "label": "girls' high school"
        },
        {
          "code": "glass_and_mirror_shop",
          "label": "glass & mirror shop"
        },
        {
          "code": "glass_block_supplier",
          "label": "glass block supplier"
        },
        {
          "code": "glass_blower",
          "label": "glass blower"
        },
        {
          "code": "glass_cutting_service",
          "label": "glass cutting service"
        },
        {
          "code": "glass_engraving",
          "label": "glass engraver"
        },
        {
          "code": "glass_etching_service",
          "label": "glass etching service"
        },
        {
          "code": "glass_industry",
          "label": "glass industry"
        },
        {
          "code": "glass_manufacturer",
          "label": "glass manufacturer"
        },
        {
          "code": "glass_merchant",
          "label": "glass merchant"
        },
        {
          "code": "glass_repair_service",
          "label": "glass repair service"
        },
        {
          "code": "glass_shop",
          "label": "glass shop"
        },
        {
          "code": "glassware_manufacturer",
          "label": "glassware manufacturer"
        },
        {
          "code": "glassware_store",
          "label": "glassware store"
        },
        {
          "code": "glassware_wholesaler",
          "label": "glassware wholesaler"
        },
        {
          "code": "glazier",
          "label": "glazier"
        },
        {
          "code": "gluten_free_restaurant",
          "label": "gluten-free restaurant"
        },
        {
          "code": "gmc_dealer",
          "label": "gmc dealer"
        },
        {
          "code": "go_kart_track",
          "label": "go-kart track"
        },
        {
          "code": "goan_restaurant",
          "label": "goan restaurant"
        },
        {
          "code": "gold_dealer",
          "label": "gold dealer"
        },
        {
          "code": "gold_mining_company",
          "label": "gold mining company"
        },
        {
          "code": "goldfish_store",
          "label": "goldfish store"
        },
        {
          "code": "goldsmith",
          "label": "goldsmith"
        },
        {
          "code": "golf_cart_dealer",
          "label": "golf cart dealer"
        },
        {
          "code": "golf_club",
          "label": "golf club"
        },
        {
          "code": "golf_course",
          "label": "golf course"
        },
        {
          "code": "golf_course_builder",
          "label": "golf course builder"
        },
        {
          "code": "golf_driving_range",
          "label": "golf driving range"
        },
        {
          "code": "golf_instructor",
          "label": "golf instructor"
        },
        {
          "code": "golf_shop",
          "label": "golf shop"
        },
        {
          "code": "gospel_church",
          "label": "gospel church"
        },
        {
          "code": "gourmet_grocery_store",
          "label": "gourmet grocery store"
        },
        {
          "code": "government_college",
          "label": "government college"
        },
        {
          "code": "government_economic_program",
          "label": "government economic program"
        },
        {
          "code": "government_hospital",
          "label": "government hospital"
        },
        {
          "code": "government_office",
          "label": "government office"
        },
        {
          "code": "government_school",
          "label": "government school"
        },
        {
          "code": "gps_supplier",
          "label": "gps supplier"
        },
        {
          "code": "graduate_school",
          "label": "graduate school"
        },
        {
          "code": "graffiti_removal_service",
          "label": "graffiti removal service"
        },
        {
          "code": "grain_elevator",
          "label": "grain elevator"
        },
        {
          "code": "grammar_school",
          "label": "grammar school"
        },
        {
          "code": "granite_supplier",
          "label": "granite supplier"
        },
        {
          "code": "graphic_designer",
          "label": "graphic designer"
        },
        {
          "code": "gravel_pit",
          "label": "gravel pit"
        },
        {
          "code": "gravel_plant",
          "label": "gravel plant"
        },
        {
          "code": "greco_roman_wrestling",
          "label": "greco-roman wrestling"
        },
        {
          "code": "greek_orthodox_church",
          "label": "greek orthodox church"
        },
        {
          "code": "greek_restaurant",
          "label": "greek restaurant"
        },
        {
          "code": "green_energy_supplier",
          "label": "green energy supplier"
        },
        {
          "code": "green_grocers",
          "label": "greengrocer"
        },
        {
          "code": "greenhouse",
          "label": "greenhouse"
        },
        {
          "code": "greeting_card_shop",
          "label": "greeting card shop"
        },
        {
          "code": "greyhound_stadium",
          "label": "greyhound stadium"
        },
        {
          "code": "grill_store",
          "label": "grill store"
        },
        {
          "code": "grocery_delivery_service",
          "label": "grocery delivery service"
        },
        {
          "code": "grocery_store",
          "label": "grocery store"
        },
        {
          "code": "ground_self_defense_force",
          "label": "ground self defense force"
        },
        {
          "code": "group_accommodation",
          "label": "group accommodation"
        },
        {
          "code": "group_home",
          "label": "group home"
        },
        {
          "code": "guardia_civil",
          "label": "guardia civil"
        },
        {
          "code": "guardia_di_finanza_police",
          "label": "guardia di finanza police"
        },
        {
          "code": "guatemalan_restaurant",
          "label": "guatemalan restaurant"
        },
        {
          "code": "guest_house",
          "label": "guest house"
        },
        {
          "code": "gui_zhou_restaurant",
          "label": "guizhou restaurant"
        },
        {
          "code": "guitar_instructor",
          "label": "guitar instructor"
        },
        {
          "code": "guitar_store",
          "label": "guitar store"
        },
        {
          "code": "gun_club",
          "label": "gun club"
        },
        {
          "code": "gun_shop",
          "label": "gun shop"
        },
        {
          "code": "guts_barbecue_restaurant",
          "label": "offal barbecue restaurant"
        },
        {
          "code": "gutter_cleaning_service",
          "label": "gutter cleaning service"
        },
        {
          "code": "gym",
          "label": "gym"
        },
        {
          "code": "gymnasium_cz",
          "label": "gymnasium cz"
        },
        {
          "code": "gymnasium_school",
          "label": "gymnasium school"
        },
        {
          "code": "gymnastics_center",
          "label": "gymnastics center"
        },
        {
          "code": "gymnastics_club",
          "label": "gymnastics club"
        },
        {
          "code": "gynecologist",
          "label": "obstetrician-gynecologist"
        },
        {
          "code": "gynecologist_only",
          "label": "gynecologist"
        },
        {
          "code": "gypsum_product_supplier",
          "label": "gypsum product supplier"
        },
        {
          "code": "gyro_restaurant",
          "label": "gyro restaurant"
        },
        {
          "code": "haberdashery",
          "label": "haberdashery"
        },
        {
          "code": "hair_extension_technician",
          "label": "hair extension technician"
        },
        {
          "code": "hair_extensions_supplier",
          "label": "hair extensions supplier"
        },
        {
          "code": "hair_removal_service",
          "label": "hair removal service"
        },
        {
          "code": "hair_replacement_service",
          "label": "hair replacement service"
        },
        {
          "code": "hair_salon",
          "label": "hair salon"
        },
        {
          "code": "hair_transplantation_clinic",
          "label": "hair transplantation clinic"
        },
        {
          "code": "haitian_restaurant",
          "label": "haitian restaurant"
        },
        {
          "code": "hakka_restaurant",
          "label": "hakka restaurant"
        },
        {
          "code": "halal_restaurant",
          "label": "halal restaurant"
        },
        {
          "code": "halfway_house",
          "label": "halfway house"
        },
        {
          "code": "ham_shop",
          "label": "ham shop"
        },
        {
          "code": "hamburger_restaurant",
          "label": "hamburger restaurant"
        },
        {
          "code": "hammam",
          "label": "hammam"
        },
        {
          "code": "hand_surgeon",
          "label": "hand surgeon"
        },
        {
          "code": "handbags_shop",
          "label": "handbags shop"
        },
        {
          "code": "handball_club",
          "label": "handball club"
        },
        {
          "code": "handball_court",
          "label": "handball court"
        },
        {
          "code": "handicapped_transportation_service",
          "label": "handicapped transportation service"
        },
        {
          "code": "handicraft",
          "label": "handicraft"
        },
        {
          "code": "handicraft_exporter",
          "label": "handicraft exporter"
        },
        {
          "code": "handicraft_fair",
          "label": "handicraft fair"
        },
        {
          "code": "handicraft_museum",
          "label": "handicraft museum"
        },
        {
          "code": "handicraft_school",
          "label": "handicraft school"
        },
        {
          "code": "handicrafts_wholesaler",
          "label": "handicrafts wholesaler"
        },
        {
          "code": "handyman",
          "label": "handyman"
        },
        {
          "code": "hang_gliding_center",
          "label": "hang gliding center"
        },
        {
          "code": "hardware_store",
          "label": "hardware store"
        },
        {
          "code": "hardware_training_institute",
          "label": "hardware training institute"
        },
        {
          "code": "harley_davidson_dealer",
          "label": "harley-davidson dealer"
        },
        {
          "code": "hat_shop",
          "label": "hat shop"
        },
        {
          "code": "haunted_house",
          "label": "haunted house"
        },
        {
          "code": "haute_couture_fashion_house",
          "label": "haute couture fashion house"
        },
        {
          "code": "haute_french_restaurant",
          "label": "haute french restaurant"
        },
        {
          "code": "hawaiian_goods_store",
          "label": "hawaiian goods store"
        },
        {
          "code": "hawaiian_restaurant",
          "label": "hawaiian restaurant"
        },
        {
          "code": "hawker_centre",
          "label": "hawker centre"
        },
        {
          "code": "hawker_stall",
          "label": "hawker stall"
        },
        {
          "code": "hay_supplier",
          "label": "hay supplier"
        },
        {
          "code": "head_start_center",
          "label": "head start center"
        },
        {
          "code": "health_and_beauty_shop",
          "label": "health and beauty shop"
        },
        {
          "code": "health_consultant",
          "label": "health consultant"
        },
        {
          "code": "health_food_restaurant",
          "label": "health food restaurant"
        },
        {
          "code": "health_food_store",
          "label": "health food store"
        },
        {
          "code": "health_insurance_agency",
          "label": "health insurance agency"
        },
        {
          "code": "health_resort",
          "label": "health resort"
        },
        {
          "code": "health_spa",
          "label": "health spa"
        },
        {
          "code": "hearing_aid_repair_service",
          "label": "hearing aid repair service"
        },
        {
          "code": "hearing_aid_store",
          "label": "hearing aid store"
        },
        {
          "code": "heart_hospital",
          "label": "heart hospital"
        },
        {
          "code": "heating_contractor",
          "label": "heating contractor"
        },
        {
          "code": "heating_equipment_supplier",
          "label": "heating equipment supplier"
        },
        {
          "code": "heating_oil_supplier",
          "label": "heating oil supplier"
        },
        {
          "code": "height_works",
          "label": "height works"
        },
        {
          "code": "helicopter_charter",
          "label": "helicopter charter"
        },
        {
          "code": "helicopter_tour_agency",
          "label": "helicopter tour agency"
        },
        {
          "code": "heliport",
          "label": "heliport"
        },
        {
          "code": "helium_gas_supplier",
          "label": "helium gas supplier"
        },
        {
          "code": "helpline",
          "label": "helpline"
        },
        {
          "code": "hematologist",
          "label": "hematologist"
        },
        {
          "code": "herb_shop",
          "label": "herb shop"
        },
        {
          "code": "herbal_medicine_store",
          "label": "herbal medicine store"
        },
        {
          "code": "herbalist",
          "label": "herbalist"
        },
        {
          "code": "heritage_building",
          "label": "heritage building"
        },
        {
          "code": "heritage_museum",
          "label": "heritage museum"
        },
        {
          "code": "heritage_preservation",
          "label": "heritage preservation"
        },
        {
          "code": "high_ropes_course",
          "label": "high ropes course"
        },
        {
          "code": "high_school",
          "label": "high school"
        },
        {
          "code": "higher_secondary_school",
          "label": "higher secondary school"
        },
        {
          "code": "highway_patrol",
          "label": "highway patrol"
        },
        {
          "code": "hiking_area",
          "label": "hiking area"
        },
        {
          "code": "hindu_priest",
          "label": "hindu priest"
        },
        {
          "code": "hindu_temple",
          "label": "hindu temple"
        },
        {
          "code": "hip_hop_dance_class",
          "label": "hip hop dance class"
        },
        {
          "code": "hispanic_church",
          "label": "hispanic church"
        },
        {
          "code": "historical_landmark",
          "label": "historical landmark"
        },
        {
          "code": "historical_place_museum",
          "label": "historical place museum"
        },
        {
          "code": "historical_society",
          "label": "historical society"
        },
        {
          "code": "history_museum",
          "label": "history museum"
        },
        {
          "code": "hiv_testing_center",
          "label": "hiv testing center"
        },
        {
          "code": "hoagie_restaurant",
          "label": "hoagie restaurant"
        },
        {
          "code": "hobby_store",
          "label": "hobby store"
        },
        {
          "code": "hockey_club",
          "label": "hockey club"
        },
        {
          "code": "hockey_field",
          "label": "hockey field"
        },
        {
          "code": "hockey_rink",
          "label": "hockey rink"
        },
        {
          "code": "hockey_supply_store",
          "label": "hockey supply store"
        },
        {
          "code": "holding_company",
          "label": "holding company"
        },
        {
          "code": "holiday_accommodation_service",
          "label": "holiday accommodation service"
        },
        {
          "code": "holiday_apartment_rental",
          "label": "holiday apartment rental"
        },
        {
          "code": "holiday_home",
          "label": "holiday home"
        },
        {
          "code": "holiday_park",
          "label": "holiday park"
        },
        {
          "code": "holistic_medicine_practitioner",
          "label": "holistic medicine practitioner"
        },
        {
          "code": "home_automation_company",
          "label": "home automation company"
        },
        {
          "code": "home_builder",
          "label": "home builder"
        },
        {
          "code": "home_cinema_installation",
          "label": "home cinema installation"
        },
        {
          "code": "home_goods_store",
          "label": "home goods store"
        },
        {
          "code": "home_hairdresser",
          "label": "home hairdresser"
        },
        {
          "code": "home_health_care_service",
          "label": "home health care service"
        },
        {
          "code": "home_help",
          "label": "home help"
        },
        {
          "code": "home_help_service_agency",
          "label": "home help service agency"
        },
        {
          "code": "home_improvement_store",
          "label": "home improvement store"
        },
        {
          "code": "home_inspector",
          "label": "home inspector"
        },
        {
          "code": "home_insurance_agency",
          "label": "home insurance agency"
        },
        {
          "code": "home_theater_store",
          "label": "home theater store"
        },
        {
          "code": "homekill_service",
          "label": "homekill service"
        },
        {
          "code": "homeless_service",
          "label": "homeless service"
        },
        {
          "code": "homeless_shelter",
          "label": "homeless shelter"
        },
        {
          "code": "homeopath",
          "label": "homeopath"
        },
        {
          "code": "homeopathic_pharmacy",
          "label": "homeopathic pharmacy"
        },
        {
          "code": "homeowners_association",
          "label": "homeowners' association"
        },
        {
          "code": "honda_dealer",
          "label": "honda dealer"
        },
        {
          "code": "honduran_restaurant",
          "label": "honduran restaurant"
        },
        {
          "code": "honey_farm",
          "label": "honey farm"
        },
        {
          "code": "hong_kong_style_fast_food_restaurant",
          "label": "hong kong style fast food restaurant"
        },
        {
          "code": "hookah_bar",
          "label": "hookah bar"
        },
        {
          "code": "hookah_store",
          "label": "hookah store"
        },
        {
          "code": "horse_boarding_stable",
          "label": "horse boarding stable"
        },
        {
          "code": "horse_breeder",
          "label": "horse breeder"
        },
        {
          "code": "horse_rental_service",
          "label": "horse rental service"
        },
        {
          "code": "horse_riding_field",
          "label": "horse riding field"
        },
        {
          "code": "horse_riding_school",
          "label": "horse riding school"
        },
        {
          "code": "horse_trailer_dealer",
          "label": "horse trailer dealer"
        },
        {
          "code": "horse_trainer",
          "label": "horse trainer"
        },
        {
          "code": "horseback_riding_service",
          "label": "horseback riding service"
        },
        {
          "code": "horsebox_specialist",
          "label": "horse transport supplier"
        },
        {
          "code": "horseshoe_smith",
          "label": "horseshoe smith"
        },
        {
          "code": "horsestable_studfarm",
          "label": "horsestable studfarm"
        },
        {
          "code": "hose_supplier",
          "label": "hose supplier"
        },
        {
          "code": "hospice",
          "label": "hospice"
        },
        {
          "code": "hospital",
          "label": "hospital"
        },
        {
          "code": "hospital_and_equipment_supplies",
          "label": "hospital equipment and supplies"
        },
        {
          "code": "hospital_department",
          "label": "hospital department"
        },
        {
          "code": "hospitality_and_tourism_school",
          "label": "hospitality and tourism school"
        },
        {
          "code": "hospitality_high_school",
          "label": "hospitality high school"
        },
        {
          "code": "host_club",
          "label": "host club"
        },
        {
          "code": "hostel",
          "label": "hostel"
        },
        {
          "code": "hot_bedstone_spa",
          "label": "hot bedstone spa"
        },
        {
          "code": "hot_dog_restaurant",
          "label": "hot dog restaurant"
        },
        {
          "code": "hot_dog_stand",
          "label": "hot dog stand"
        },
        {
          "code": "hot_pot_restaurant",
          "label": "hot pot restaurant"
        },
        {
          "code": "hot_spring_hotel",
          "label": "hot spring hotel"
        },
        {
          "code": "hot_tub_repair_service",
          "label": "hot tub repair service"
        },
        {
          "code": "hot_tub_store",
          "label": "hot tub store"
        },
        {
          "code": "hot_water_system_supplier",
          "label": "hot water system supplier"
        },
        {
          "code": "hotel",
          "label": "hotel"
        },
        {
          "code": "hotel_management_school",
          "label": "hotel management school"
        },
        {
          "code": "hotel_supply_store",
          "label": "hotel supply store"
        },
        {
          "code": "house_cleaning_service",
          "label": "house cleaning service"
        },
        {
          "code": "house_clearance_service",
          "label": "house clearance service"
        },
        {
          "code": "house_sitter",
          "label": "house sitter"
        },
        {
          "code": "house_sitter_agency",
          "label": "house sitter agency"
        },
        {
          "code": "houseboat_rental_service",
          "label": "houseboat rental service"
        },
        {
          "code": "household_chemicals_supplier",
          "label": "household chemicals supplier"
        },
        {
          "code": "household_goods_wholesaler",
          "label": "household goods wholesaler"
        },
        {
          "code": "housing_association",
          "label": "housing association"
        },
        {
          "code": "housing_authority",
          "label": "housing authority"
        },
        {
          "code": "housing_complex",
          "label": "housing complex"
        },
        {
          "code": "housing_cooperative",
          "label": "housing cooperative"
        },
        {
          "code": "housing_development",
          "label": "housing development"
        },
        {
          "code": "housing_society",
          "label": "housing society"
        },
        {
          "code": "housing_utility_company",
          "label": "housing utility company"
        },
        {
          "code": "hua_gong_shop",
          "label": "hua gong shop"
        },
        {
          "code": "hua_niao_market_place",
          "label": "hua niao market place"
        },
        {
          "code": "hub_cap_supplier",
          "label": "hub cap supplier"
        },
        {
          "code": "huissier",
          "label": "huissier"
        },
        {
          "code": "human_ressource_consulting",
          "label": "human resource consulting"
        },
        {
          "code": "hunan_style_restaurant",
          "label": "hunan restaurant"
        },
        {
          "code": "hungarian_restaurant",
          "label": "hungarian restaurant"
        },
        {
          "code": "hunting_and_fishing_store",
          "label": "hunting and fishing store"
        },
        {
          "code": "hunting_area",
          "label": "hunting area"
        },
        {
          "code": "hunting_club",
          "label": "hunting club"
        },
        {
          "code": "hunting_preserve",
          "label": "hunting preserve"
        },
        {
          "code": "hunting_store",
          "label": "hunting store"
        },
        {
          "code": "hvac_contractor",
          "label": "hvac contractor"
        },
        {
          "code": "hydraulic_engineer",
          "label": "hydraulic engineer"
        },
        {
          "code": "hydraulic_equipment_supplier",
          "label": "hydraulic equipment supplier"
        },
        {
          "code": "hydraulic_repair_service",
          "label": "hydraulic repair service"
        },
        {
          "code": "hydroelectric_power_plant",
          "label": "hydroelectric power plant"
        },
        {
          "code": "hydroponics_equipment_supplier",
          "label": "hydroponics equipment supplier"
        },
        {
          "code": "hygiene_articles_wholesaler",
          "label": "hygiene articles wholesaler"
        },
        {
          "code": "hygiene_station",
          "label": "hygiene station"
        },
        {
          "code": "hypermarket",
          "label": "hypermarket"
        },
        {
          "code": "hypnotherapy_service",
          "label": "hypnotherapy service"
        },
        {
          "code": "hyundai_dealer",
          "label": "hyundai dealer"
        },
        {
          "code": "ice_cream_equipment_supplier",
          "label": "ice cream equipment supplier"
        },
        {
          "code": "ice_cream_shop",
          "label": "ice cream shop"
        },
        {
          "code": "ice_hockey_club",
          "label": "ice hockey club"
        },
        {
          "code": "ice_skating_club",
          "label": "ice skating club"
        },
        {
          "code": "ice_skating_instructor",
          "label": "ice skating instructor"
        },
        {
          "code": "ice_skating_rink",
          "label": "ice skating rink"
        },
        {
          "code": "ice_supplier",
          "label": "ice supplier"
        },
        {
          "code": "icelandic_restaurant",
          "label": "icelandic restaurant"
        },
        {
          "code": "icse_school",
          "label": "icse school"
        },
        {
          "code": "idol_manufacturer",
          "label": "idol manufacturer"
        },
        {
          "code": "ikan_bakar_restaurant",
          "label": "ikan bakar restaurant"
        },
        {
          "code": "image_consultant",
          "label": "image consultant"
        },
        {
          "code": "imax_theater",
          "label": "imax theater"
        },
        {
          "code": "immigration_and_naturalization_service",
          "label": "immigration & naturalization service"
        },
        {
          "code": "immigration_attorney",
          "label": "immigration attorney"
        },
        {
          "code": "immigration_detention_center",
          "label": "immigration detention centre"
        },
        {
          "code": "immunologist",
          "label": "immunologist"
        },
        {
          "code": "impermeabilization_service",
          "label": "impermeabilization service"
        },
        {
          "code": "import_export_company",
          "label": "import export company"
        },
        {
          "code": "importer",
          "label": "importer"
        },
        {
          "code": "incense_supplier",
          "label": "incense supplier"
        },
        {
          "code": "incineration_plant",
          "label": "incineration plant"
        },
        {
          "code": "income_protection_insurance",
          "label": "income protection insurance"
        },
        {
          "code": "income_tax_help_association",
          "label": "income tax help association"
        },
        {
          "code": "indian_grocery_store",
          "label": "indian grocery store"
        },
        {
          "code": "indian_muslim_restaurant",
          "label": "indian muslim restaurant"
        },
        {
          "code": "indian_restaurant",
          "label": "indian restaurant"
        },
        {
          "code": "indian_sizzler_restaurant",
          "label": "indian sizzler restaurant"
        },
        {
          "code": "indian_takeaway",
          "label": "indian takeaway"
        },
        {
          "code": "indonesian_restaurant",
          "label": "indonesian restaurant"
        },
        {
          "code": "indoor_cycling",
          "label": "indoor cycling"
        },
        {
          "code": "indoor_golf_course",
          "label": "indoor golf course"
        },
        {
          "code": "indoor_lodging",
          "label": "indoor lodging"
        },
        {
          "code": "indoor_playground",
          "label": "indoor playground"
        },
        {
          "code": "indoor_snowcenter",
          "label": "indoor snowcenter"
        },
        {
          "code": "indoor_swimming_pool",
          "label": "indoor swimming pool"
        },
        {
          "code": "industrial_area",
          "label": "industrial area"
        },
        {
          "code": "industrial_chemicals_wholesaler",
          "label": "industrial chemicals wholesaler"
        },
        {
          "code": "industrial_consultant",
          "label": "industrial consultant"
        },
        {
          "code": "industrial_design_company",
          "label": "industrial design company"
        },
        {
          "code": "industrial_door_supplier",
          "label": "industrial door supplier"
        },
        {
          "code": "industrial_engineer",
          "label": "industrial engineer"
        },
        {
          "code": "industrial_engineers_association",
          "label": "industrial engineers association"
        },
        {
          "code": "industrial_equipment_supplier",
          "label": "industrial equipment supplier"
        },
        {
          "code": "industrial_framework_supplier",
          "label": "industrial framework supplier"
        },
        {
          "code": "industrial_gas_supplier",
          "label": "industrial gas supplier"
        },
        {
          "code": "industrial_real_estate_agency",
          "label": "industrial real estate agency"
        },
        {
          "code": "industrial_supermarket",
          "label": "industrial supermarket"
        },
        {
          "code": "industrial_technical_engineers_association",
          "label": "industrial technical engineers association"
        },
        {
          "code": "industrial_vacuum_equipment_supplier",
          "label": "industrial vacuum equipment supplier"
        },
        {
          "code": "infectious_disease_physician",
          "label": "infectious disease physician"
        },
        {
          "code": "infiniti_dealer",
          "label": "infiniti dealer"
        },
        {
          "code": "information_bureau",
          "label": "information bureau"
        },
        {
          "code": "information_services",
          "label": "information services"
        },
        {
          "code": "inn",
          "label": "inn"
        },
        {
          "code": "insolvency_service",
          "label": "insolvency service"
        },
        {
          "code": "institute_of_geography_and_statistics",
          "label": "institute of geography and statistics"
        },
        {
          "code": "instrumentation_engineer",
          "label": "instrumentation engineer"
        },
        {
          "code": "insulation_contractor",
          "label": "insulation contractor"
        },
        {
          "code": "insulation_materials_store",
          "label": "insulation materials store"
        },
        {
          "code": "insulator_supplier",
          "label": "insulator supplier"
        },
        {
          "code": "insurance_agency",
          "label": "insurance agency"
        },
        {
          "code": "insurance_attorney",
          "label": "insurance attorney"
        },
        {
          "code": "insurance_broker",
          "label": "insurance broker"
        },
        {
          "code": "insurance_company",
          "label": "insurance company"
        },
        {
          "code": "insurance_school",
          "label": "insurance school"
        },
        {
          "code": "intellectual_property_registry",
          "label": "intellectual property registry"
        },
        {
          "code": "interior_architect_office",
          "label": "interior architect office"
        },
        {
          "code": "interior_construction_contractor",
          "label": "interior construction contractor"
        },
        {
          "code": "interior_designer",
          "label": "interior designer"
        },
        {
          "code": "interior_door",
          "label": "interior door"
        },
        {
          "code": "interior_fitting_contractor",
          "label": "interior fitting contractor"
        },
        {
          "code": "interior_plant_service",
          "label": "interior plant service"
        },
        {
          "code": "internal_medicine_ward",
          "label": "internal medicine ward"
        },
        {
          "code": "international_airport",
          "label": "international airport"
        },
        {
          "code": "international_school",
          "label": "international school"
        },
        {
          "code": "international_trade_consultant",
          "label": "international trade consultant"
        },
        {
          "code": "internet_cafe",
          "label": "internet cafe"
        },
        {
          "code": "internet_marketing_service",
          "label": "internet marketing service"
        },
        {
          "code": "internet_service_provider",
          "label": "internet service provider"
        },
        {
          "code": "internet_shop",
          "label": "internet shop"
        },
        {
          "code": "internist",
          "label": "internist"
        },
        {
          "code": "investment_bank",
          "label": "investment bank"
        },
        {
          "code": "investment_company",
          "label": "investment company"
        },
        {
          "code": "investment_service",
          "label": "investment service"
        },
        {
          "code": "invitation_printing_service",
          "label": "invitation printing service"
        },
        {
          "code": "irish_goods_store",
          "label": "irish goods store"
        },
        {
          "code": "irish_pub",
          "label": "irish pub"
        },
        {
          "code": "irish_restaurant",
          "label": "irish restaurant"
        },
        {
          "code": "iron_steel_contractor",
          "label": "iron steel contractor"
        },
        {
          "code": "iron_ware_dealer",
          "label": "iron ware dealer"
        },
        {
          "code": "iron_works",
          "label": "iron works"
        },
        {
          "code": "irrigation_equipment_supplier",
          "label": "irrigation equipment supplier"
        },
        {
          "code": "israeli_restaurant",
          "label": "israeli restaurant"
        },
        {
          "code": "isuzu_dealer",
          "label": "isuzu dealer"
        },
        {
          "code": "italian_grocery_store",
          "label": "italian grocery store"
        },
        {
          "code": "italian_restaurant",
          "label": "italian restaurant"
        },
        {
          "code": "iup",
          "label": "iup"
        },
        {
          "code": "iut",
          "label": "institute of technology"
        },
        {
          "code": "jaguar_dealer",
          "label": "jaguar dealer"
        },
        {
          "code": "jain_temple",
          "label": "jain temple"
        },
        {
          "code": "jamaican_restaurant",
          "label": "jamaican restaurant"
        },
        {
          "code": "janitorial_equipment_supplier",
          "label": "janitorial equipment supplier"
        },
        {
          "code": "janitorial_service",
          "label": "janitorial service"
        },
        {
          "code": "japanese_authentic_restaurant",
          "label": "authentic japanese restaurant"
        },
        {
          "code": "japanese_cheap_sweets_shop",
          "label": "japanese cheap sweets shop"
        },
        {
          "code": "japanese_confectionery_shop",
          "label": "japanese confectionery shop"
        },
        {
          "code": "japanese_curry_restaurant",
          "label": "japanese curry restaurant"
        },
        {
          "code": "japanese_delicatessen",
          "label": "japanese delicatessen"
        },
        {
          "code": "japanese_grocery_store",
          "label": "japanese grocery store"
        },
        {
          "code": "japanese_high_quality_restaurant",
          "label": "ryotei restaurant"
        },
        {
          "code": "japanese_inns",
          "label": "japanese inn"
        },
        {
          "code": "japanese_izakaya_restaurant",
          "label": "izakaya restaurant"
        },
        {
          "code": "japanese_language_instructor",
          "label": "japanese language instructor"
        },
        {
          "code": "japanese_regional_restaurant",
          "label": "japanese regional restaurant"
        },
        {
          "code": "japanese_restaurant",
          "label": "japanese restaurant"
        },
        {
          "code": "japanese_steakhouse",
          "label": "japanese steakhouse"
        },
        {
          "code": "japanese_sweets_restaurant",
          "label": "japanese sweets restaurant"
        },
        {
          "code": "japanized_western_food_restaurant",
          "label": "japanized western restaurant"
        },
        {
          "code": "javanese_restaurant",
          "label": "javanese restaurant"
        },
        {
          "code": "jazz_club",
          "label": "jazz club"
        },
        {
          "code": "jeep_dealer",
          "label": "jeep dealer"
        },
        {
          "code": "jehovahs_witness_church",
          "label": "jehovah's witness kingdom hall"
        },
        {
          "code": "jeweler",
          "label": "jeweler"
        },
        {
          "code": "jewelry_appraiser",
          "label": "jewelry appraiser"
        },
        {
          "code": "jewelry_buyer",
          "label": "jewelry buyer"
        },
        {
          "code": "jewelry_designer",
          "label": "jewelry designer"
        },
        {
          "code": "jewelry_engraver",
          "label": "jewelry engraver"
        },
        {
          "code": "jewelry_equipment_supplier",
          "label": "jewelry equipment supplier"
        },
        {
          "code": "jewelry_exporter",
          "label": "jewelry exporter"
        },
        {
          "code": "jewelry_manufacturer",
          "label": "jewellery manufacturer"
        },
        {
          "code": "jewelry_repair_service",
          "label": "jewelry repair service"
        },
        {
          "code": "jewelry_store",
          "label": "jewelry store"
        },
        {
          "code": "jewish_restaurant",
          "label": "jewish restaurant"
        },
        {
          "code": "jiang_su_restaurant",
          "label": "jiangsu restaurant"
        },
        {
          "code": "joiner",
          "label": "joiner"
        },
        {
          "code": "judicial_auction",
          "label": "judicial auction"
        },
        {
          "code": "judicial_scrivener",
          "label": "judicial scrivener"
        },
        {
          "code": "judo_club",
          "label": "judo club"
        },
        {
          "code": "judo_school",
          "label": "judo school"
        },
        {
          "code": "juice_shop",
          "label": "juice shop"
        },
        {
          "code": "jujitsu_school",
          "label": "jujitsu school"
        },
        {
          "code": "junior_college",
          "label": "junior college"
        },
        {
          "code": "junk_dealer",
          "label": "junk dealer"
        },
        {
          "code": "junk_store",
          "label": "junk store"
        },
        {
          "code": "junkyard",
          "label": "junkyard"
        },
        {
          "code": "justice_department",
          "label": "justice department"
        },
        {
          "code": "jute_exporter",
          "label": "jute exporter"
        },
        {
          "code": "jute_mill",
          "label": "jute mill"
        },
        {
          "code": "juvenile_detention_center",
          "label": "juvenile detention center"
        },
        {
          "code": "kabaddi_club",
          "label": "kabaddi club"
        },
        {
          "code": "kaiseki_restaurant",
          "label": "kaiseki restaurant"
        },
        {
          "code": "karaoke",
          "label": "karaoke"
        },
        {
          "code": "karaoke_bar",
          "label": "karaoke bar"
        },
        {
          "code": "karaoke_equipment_rental_service",
          "label": "karaoke equipment rental service"
        },
        {
          "code": "karate_club",
          "label": "karate club"
        },
        {
          "code": "karate_school",
          "label": "karate school"
        },
        {
          "code": "karma_dealer",
          "label": "karma dealer"
        },
        {
          "code": "karnataka_restaurant",
          "label": "karnataka restaurant"
        },
        {
          "code": "kashmiri_restaurant",
          "label": "kashmiri restaurant"
        },
        {
          "code": "kawasaki_motorcycle_dealer",
          "label": "kawasaki motorcycle dealer"
        },
        {
          "code": "kazakhstani_restaurant",
          "label": "kazakhstani restaurant"
        },
        {
          "code": "kebab_shop",
          "label": "kebab shop"
        },
        {
          "code": "kennel",
          "label": "kennel"
        },
        {
          "code": "kerosene_supplier",
          "label": "kerosene supplier"
        },
        {
          "code": "key_duplication_service",
          "label": "key duplication service"
        },
        {
          "code": "kia_dealer",
          "label": "kia dealer"
        },
        {
          "code": "kickboxing_school",
          "label": "kickboxing school"
        },
        {
          "code": "kilt_shop_and_hire",
          "label": "kilt shop and hire"
        },
        {
          "code": "kimono_store",
          "label": "kimono store"
        },
        {
          "code": "kindergarten",
          "label": "kindergarten"
        },
        {
          "code": "kinesiologist",
          "label": "kinesiologist"
        },
        {
          "code": "kiosk",
          "label": "kiosk"
        },
        {
          "code": "kitchen_furniture_store",
          "label": "kitchen furniture store"
        },
        {
          "code": "kitchen_remodeler",
          "label": "kitchen remodeler"
        },
        {
          "code": "kitchen_supply_store",
          "label": "kitchen supply store"
        },
        {
          "code": "kite_shop",
          "label": "kite shop"
        },
        {
          "code": "knife_manufacturing",
          "label": "knife manufacturing"
        },
        {
          "code": "knife_store",
          "label": "knife store"
        },
        {
          "code": "knit_shop",
          "label": "knit shop"
        },
        {
          "code": "knitting_instructor",
          "label": "knitting instructor"
        },
        {
          "code": "knitwear_manufacturer",
          "label": "knitwear manufacturer"
        },
        {
          "code": "konkani_restaurant",
          "label": "konkani restaurant"
        },
        {
          "code": "korean_barbecue_restaurant",
          "label": "korean barbecue restaurant"
        },
        {
          "code": "korean_beef_restaurant",
          "label": "korean beef restaurant"
        },
        {
          "code": "korean_church",
          "label": "korean church"
        },
        {
          "code": "korean_grocery_store",
          "label": "korean grocery store"
        },
        {
          "code": "korean_restaurant",
          "label": "korean restaurant"
        },
        {
          "code": "korean_rib_restaurant",
          "label": "korean rib restaurant"
        },
        {
          "code": "kosher_grocery_store",
          "label": "kosher grocery store"
        },
        {
          "code": "kosher_restaurant",
          "label": "kosher restaurant"
        },
        {
          "code": "kung_fu_school",
          "label": "kung fu school"
        },
        {
          "code": "kushiyaki_restaurant",
          "label": "kushiyaki restaurant"
        },
        {
          "code": "kyoto_cuisine_restaurant",
          "label": "kyoto style japanese restaurant"
        },
        {
          "code": "labor_relations_attorney",
          "label": "labor relations attorney"
        },
        {
          "code": "labor_union",
          "label": "labor union"
        },
        {
          "code": "laboratory",
          "label": "laboratory"
        },
        {
          "code": "laboratory_equipment_supplier",
          "label": "laboratory equipment supplier"
        },
        {
          "code": "labour_club",
          "label": "labour club"
        },
        {
          "code": "ladder_supplier",
          "label": "ladder supplier"
        },
        {
          "code": "lamborghini_dealer",
          "label": "lamborghini dealer"
        },
        {
          "code": "laminating_equipment_supplier",
          "label": "laminating equipment supplier"
        },
        {
          "code": "lamination_service",
          "label": "lamination service"
        },
        {
          "code": "lamp_repair_service",
          "label": "lamp repair service"
        },
        {
          "code": "lamp_shade_supplier",
          "label": "lamp shade supplier"
        },
        {
          "code": "land_allotment",
          "label": "land allotment"
        },
        {
          "code": "land_planning_authority",
          "label": "land planning authority"
        },
        {
          "code": "land_reform_institute",
          "label": "land reform institute"
        },
        {
          "code": "land_rover_dealer",
          "label": "land rover dealer"
        },
        {
          "code": "land_surveying_office",
          "label": "land surveying office"
        },
        {
          "code": "land_surveyor",
          "label": "land surveyor"
        },
        {
          "code": "landscape_architect",
          "label": "landscape architect"
        },
        {
          "code": "landscape_designer",
          "label": "landscape designer"
        },
        {
          "code": "landscape_lighting_designer",
          "label": "landscape lighting designer"
        },
        {
          "code": "landscaper",
          "label": "landscaper"
        },
        {
          "code": "landscaping_supply_store",
          "label": "landscaping supply store"
        },
        {
          "code": "language_school",
          "label": "language school"
        },
        {
          "code": "laotian_restaurant",
          "label": "laotian restaurant"
        },
        {
          "code": "lapidary",
          "label": "lapidary"
        },
        {
          "code": "laser_cutting_service",
          "label": "laser cutting service"
        },
        {
          "code": "laser_equipment_supplier",
          "label": "laser equipment supplier"
        },
        {
          "code": "laser_hair_removal_service",
          "label": "laser hair removal service"
        },
        {
          "code": "laser_tag_center",
          "label": "laser tag center"
        },
        {
          "code": "lasik_surgeon",
          "label": "lasik surgeon"
        },
        {
          "code": "latin_american_restaurant",
          "label": "latin american restaurant"
        },
        {
          "code": "laundromat",
          "label": "laundromat"
        },
        {
          "code": "laundry",
          "label": "laundry"
        },
        {
          "code": "laundry_service",
          "label": "laundry service"
        },
        {
          "code": "law_book_store",
          "label": "law book store"
        },
        {
          "code": "law_firm",
          "label": "law firm"
        },
        {
          "code": "law_library",
          "label": "law library"
        },
        {
          "code": "law_school",
          "label": "law school"
        },
        {
          "code": "lawn_bowls_club",
          "label": "lawn bowls club"
        },
        {
          "code": "lawn_care_service",
          "label": "lawn care service"
        },
        {
          "code": "lawn_equipment_rental_service",
          "label": "lawn equipment rental service"
        },
        {
          "code": "lawn_irrigation_equipment_supplier",
          "label": "lawn irrigation equipment supplier"
        },
        {
          "code": "lawn_mower_repair_service",
          "label": "lawn mower repair service"
        },
        {
          "code": "lawn_mower_store",
          "label": "lawn mower store"
        },
        {
          "code": "lawn_sprinkler_system_contractor",
          "label": "lawn sprinkler system contractor"
        },
        {
          "code": "lawyer",
          "label": "lawyer"
        },
        {
          "code": "lawyers_association",
          "label": "lawyers association"
        },
        {
          "code": "leagues_club",
          "label": "leagues club"
        },
        {
          "code": "learner_driver_training_area",
          "label": "learner driver training area"
        },
        {
          "code": "learning_center",
          "label": "learning center"
        },
        {
          "code": "leasing_service",
          "label": "leasing service"
        },
        {
          "code": "leather_cleaning_service",
          "label": "leather cleaning service"
        },
        {
          "code": "leather_coats_store",
          "label": "leather coats store"
        },
        {
          "code": "leather_exporter",
          "label": "leather exporter"
        },
        {
          "code": "leather_goods_manufacturer",
          "label": "leather goods manufacturer"
        },
        {
          "code": "leather_goods_store",
          "label": "leather goods store"
        },
        {
          "code": "leather_goods_supplier",
          "label": "leather goods supplier"
        },
        {
          "code": "leather_goods_wholesaler",
          "label": "leather goods wholesaler"
        },
        {
          "code": "leather_repair_service",
          "label": "leather repair service"
        },
        {
          "code": "leather_wholesaler",
          "label": "leather wholesaler"
        },
        {
          "code": "lebanese_restaurant",
          "label": "lebanese restaurant"
        },
        {
          "code": "legal_affairs_bureau",
          "label": "legal affairs bureau"
        },
        {
          "code": "legal_aid_office",
          "label": "legal aid office"
        },
        {
          "code": "legal_services",
          "label": "legal services"
        },
        {
          "code": "legally_defined_lodging",
          "label": "legally defined lodging"
        },
        {
          "code": "leisurecentre",
          "label": "leisure centre"
        },
        {
          "code": "lexus_dealer",
          "label": "lexus dealer"
        },
        {
          "code": "library",
          "label": "library"
        },
        {
          "code": "license_bureau",
          "label": "license bureau"
        },
        {
          "code": "license_plate_frames_supplier",
          "label": "license plate frames supplier"
        },
        {
          "code": "lido",
          "label": "lido"
        },
        {
          "code": "life_coach",
          "label": "life coach"
        },
        {
          "code": "life_insurance_agency",
          "label": "life insurance agency"
        },
        {
          "code": "light_bulb_supplier",
          "label": "light bulb supplier"
        },
        {
          "code": "lighting_consultant",
          "label": "lighting consultant"
        },
        {
          "code": "lighting_contractor",
          "label": "lighting contractor"
        },
        {
          "code": "lighting_manufacturer",
          "label": "lighting manufacturer"
        },
        {
          "code": "lighting_store",
          "label": "lighting store"
        },
        {
          "code": "lighting_wholesaler",
          "label": "lighting wholesaler"
        },
        {
          "code": "ligurian_restaurant",
          "label": "ligurian restaurant"
        },
        {
          "code": "limousine_service",
          "label": "limousine service"
        },
        {
          "code": "lincoln_mercury_dealer",
          "label": "lincoln dealer"
        },
        {
          "code": "line_marking_service",
          "label": "line marking service"
        },
        {
          "code": "linens_store",
          "label": "linens store"
        },
        {
          "code": "lingerie_manufacturer",
          "label": "lingerie manufacturer"
        },
        {
          "code": "lingerie_store",
          "label": "lingerie store"
        },
        {
          "code": "lingerie_wholesaler",
          "label": "lingerie wholesaler"
        },
        {
          "code": "linoleum_store",
          "label": "linoleum store"
        },
        {
          "code": "liquidator",
          "label": "liquidator"
        },
        {
          "code": "liquor_store",
          "label": "liquor store"
        },
        {
          "code": "liquor_wholesaler",
          "label": "liquor wholesaler"
        },
        {
          "code": "literacy_program",
          "label": "literacy program"
        },
        {
          "code": "lithuanian_restaurant",
          "label": "lithuanian restaurant"
        },
        {
          "code": "little_league_club",
          "label": "little league club"
        },
        {
          "code": "little_league_field",
          "label": "little league field"
        },
        {
          "code": "live_music_bar",
          "label": "live music bar"
        },
        {
          "code": "live_music_venue",
          "label": "live music venue"
        },
        {
          "code": "livery_company",
          "label": "livery company"
        },
        {
          "code": "livestock_auction_house",
          "label": "livestock auction house"
        },
        {
          "code": "livestock_breeder",
          "label": "livestock breeder"
        },
        {
          "code": "livestock_dealer",
          "label": "livestock dealer"
        },
        {
          "code": "livestock_producer",
          "label": "livestock producer"
        },
        {
          "code": "loan_agency",
          "label": "loan agency"
        },
        {
          "code": "local_government_office",
          "label": "local government office"
        },
        {
          "code": "local_history_museum",
          "label": "local history museum"
        },
        {
          "code": "local_medical_services",
          "label": "local medical services"
        },
        {
          "code": "locks_supplier",
          "label": "locks supplier"
        },
        {
          "code": "locksmith",
          "label": "locksmith"
        },
        {
          "code": "lodge",
          "label": "lodge"
        },
        {
          "code": "lodging",
          "label": "lodging"
        },
        {
          "code": "log_cabins",
          "label": "log cabins"
        },
        {
          "code": "log_home_builder",
          "label": "log home builder"
        },
        {
          "code": "logging_contractor",
          "label": "logging contractor"
        },
        {
          "code": "logistics_service",
          "label": "logistics service"
        },
        {
          "code": "lombardian_restaurant",
          "label": "lombardian restaurant"
        },
        {
          "code": "loss_adjuster",
          "label": "loss adjuster"
        },
        {
          "code": "lost_property_office",
          "label": "lost property office"
        },
        {
          "code": "lottery_retailer",
          "label": "lottery retailer"
        },
        {
          "code": "lottery_shop",
          "label": "lottery shop"
        },
        {
          "code": "lounge",
          "label": "lounge"
        },
        {
          "code": "love_hotel",
          "label": "love hotel"
        },
        {
          "code": "low_emission_zone",
          "label": "low emission zone"
        },
        {
          "code": "low_income_housing_program",
          "label": "low income housing program"
        },
        {
          "code": "lpg_conversion",
          "label": "lpg conversion"
        },
        {
          "code": "luggage_repair_service",
          "label": "luggage repair service"
        },
        {
          "code": "luggage_store",
          "label": "luggage store"
        },
        {
          "code": "luggage_wholesaler",
          "label": "luggage wholesaler"
        },
        {
          "code": "lumber_store",
          "label": "lumber store"
        },
        {
          "code": "lunch_restaurant",
          "label": "lunch restaurant"
        },
        {
          "code": "lutheran_church",
          "label": "lutheran church"
        },
        {
          "code": "lyceum",
          "label": "lyceum"
        },
        {
          "code": "lymph_drainage",
          "label": "lymph drainage therapist"
        },
        {
          "code": "machine_construction",
          "label": "machine construction"
        },
        {
          "code": "machine_knife_supplier",
          "label": "machine knife supplier"
        },
        {
          "code": "machine_maintenance",
          "label": "machine maintenance"
        },
        {
          "code": "machine_repair_service",
          "label": "machine repair service"
        },
        {
          "code": "machine_shop",
          "label": "machine shop"
        },
        {
          "code": "machine_workshop",
          "label": "machine workshop"
        },
        {
          "code": "machinery_parts_manufacturer",
          "label": "machinery parts manufacturer"
        },
        {
          "code": "machining_manufacturer",
          "label": "machining manufacturer"
        },
        {
          "code": "macrobiotic_restaurant",
          "label": "macrobiotic restaurant"
        },
        {
          "code": "madrilian_restaurant",
          "label": "madrilian restaurant"
        },
        {
          "code": "magazine_store",
          "label": "magazine store"
        },
        {
          "code": "magic_store",
          "label": "magic store"
        },
        {
          "code": "magician",
          "label": "magician"
        },
        {
          "code": "mah_jong_house",
          "label": "mahjong house"
        },
        {
          "code": "mailbox_rental_service",
          "label": "mailbox rental service"
        },
        {
          "code": "mailbox_supplier",
          "label": "mailbox supplier"
        },
        {
          "code": "mailing_machine_supplier",
          "label": "mailing machine supplier"
        },
        {
          "code": "mailing_service",
          "label": "mailing service"
        },
        {
          "code": "main_customs_office",
          "label": "main customs office"
        },
        {
          "code": "majorcan_restaurant",
          "label": "majorcan restaurant"
        },
        {
          "code": "makerspace",
          "label": "makerspace"
        },
        {
          "code": "makeup_artist",
          "label": "make-up artist"
        },
        {
          "code": "malaysian_restaurant",
          "label": "malaysian restaurant"
        },
        {
          "code": "maltese_restaurant",
          "label": "maltese restaurant"
        },
        {
          "code": "mammography_service",
          "label": "mammography service"
        },
        {
          "code": "manado_restaurant",
          "label": "manado restaurant"
        },
        {
          "code": "management_school",
          "label": "management school"
        },
        {
          "code": "mandarin_restaurant",
          "label": "mandarin restaurant"
        },
        {
          "code": "manor_house",
          "label": "manor house"
        },
        {
          "code": "manufactured_home_transporter",
          "label": "manufactured home transporter"
        },
        {
          "code": "manufacturer",
          "label": "manufacturer"
        },
        {
          "code": "maori_organization",
          "label": "maori organization"
        },
        {
          "code": "map_store",
          "label": "map store"
        },
        {
          "code": "mapping_service",
          "label": "mapping service"
        },
        {
          "code": "marae",
          "label": "marae"
        },
        {
          "code": "marble_contractor",
          "label": "marble contractor"
        },
        {
          "code": "marble_supplier",
          "label": "marble supplier"
        },
        {
          "code": "marche_restaurant",
          "label": "marche restaurant"
        },
        {
          "code": "marina",
          "label": "marina"
        },
        {
          "code": "marine_engineer",
          "label": "marine engineer"
        },
        {
          "code": "marine_self_defense_force",
          "label": "marine self defense force"
        },
        {
          "code": "marine_supply_store",
          "label": "marine supply store"
        },
        {
          "code": "marine_surveyor",
          "label": "marine surveyor"
        },
        {
          "code": "maritime_museum",
          "label": "maritime museum"
        },
        {
          "code": "market",
          "label": "market"
        },
        {
          "code": "market_operator",
          "label": "market operator"
        },
        {
          "code": "market_researcher",
          "label": "market researcher"
        },
        {
          "code": "marketing_agency",
          "label": "marketing agency"
        },
        {
          "code": "marketing_consultant",
          "label": "marketing consultant"
        },
        {
          "code": "markmens_clubhouse",
          "label": "markmens clubhouse"
        },
        {
          "code": "marquee_hire",
          "label": "marquee hire service"
        },
        {
          "code": "marriage_celebrant",
          "label": "marriage celebrant"
        },
        {
          "code": "marriage_counselor",
          "label": "marriage counselor"
        },
        {
          "code": "marriage_license_bureau",
          "label": "marriage license bureau"
        },
        {
          "code": "martial_arts_club",
          "label": "martial arts club"
        },
        {
          "code": "martial_arts_school",
          "label": "martial arts school"
        },
        {
          "code": "martial_arts_supply_store",
          "label": "martial arts supply store"
        },
        {
          "code": "maserati_dealer",
          "label": "maserati dealer"
        },
        {
          "code": "masonic_building",
          "label": "masonic center"
        },
        {
          "code": "masonry_contractor",
          "label": "masonry contractor"
        },
        {
          "code": "masonry_supply_store",
          "label": "masonry supply store"
        },
        {
          "code": "massage_school",
          "label": "massage school"
        },
        {
          "code": "massage_spa",
          "label": "massage spa"
        },
        {
          "code": "massage_supply_store",
          "label": "massage supply store"
        },
        {
          "code": "massage_therapist",
          "label": "massage therapist"
        },
        {
          "code": "match_box_manufacturer",
          "label": "match box manufacturer"
        },
        {
          "code": "material_handling_equipment_supplier",
          "label": "material handling equipment supplier"
        },
        {
          "code": "maternity_hospital",
          "label": "maternity hospital"
        },
        {
          "code": "maternity_store",
          "label": "maternity store"
        },
        {
          "code": "mathematics_school",
          "label": "mathematics school"
        },
        {
          "code": "mattress_store",
          "label": "mattress store"
        },
        {
          "code": "mausoleum_builder",
          "label": "mausoleum builder"
        },
        {
          "code": "maybach_dealer",
          "label": "maybach dealer"
        },
        {
          "code": "mazda_dealer",
          "label": "mazda dealer"
        },
        {
          "code": "mclaren_dealer",
          "label": "mclaren dealer"
        },
        {
          "code": "meal_delivery",
          "label": "meal delivery"
        },
        {
          "code": "meal_takeaway",
          "label": "takeout restaurant"
        },
        {
          "code": "measuring_instruments_supplier",
          "label": "measuring instruments supplier"
        },
        {
          "code": "meat_packer",
          "label": "meat packer"
        },
        {
          "code": "meat_processor",
          "label": "meat processor"
        },
        {
          "code": "meat_products",
          "label": "meat products"
        },
        {
          "code": "meat_restaurant",
          "label": "meat dish restaurant"
        },
        {
          "code": "meat_wholesaler",
          "label": "meat wholesaler"
        },
        {
          "code": "mechanic",
          "label": "mechanic"
        },
        {
          "code": "mechanical_contractor",
          "label": "mechanical contractor"
        },
        {
          "code": "mechanical_engineer",
          "label": "mechanical engineer"
        },
        {
          "code": "mechanical_plant",
          "label": "mechanical plant"
        },
        {
          "code": "media_and_information_sciences_faculty",
          "label": "media and information sciences faculty"
        },
        {
          "code": "media_company",
          "label": "media company"
        },
        {
          "code": "media_consultant",
          "label": "media consultant"
        },
        {
          "code": "media_house",
          "label": "media house"
        },
        {
          "code": "mediation_service",
          "label": "mediation service"
        },
        {
          "code": "medical_billing_service",
          "label": "medical billing service"
        },
        {
          "code": "medical_book_store",
          "label": "medical book store"
        },
        {
          "code": "medical_center",
          "label": "medical center"
        },
        {
          "code": "medical_certificate_service",
          "label": "medical certificate service"
        },
        {
          "code": "medical_clinic",
          "label": "medical clinic"
        },
        {
          "code": "medical_diagnostic_imaging_center",
          "label": "medical diagnostic imaging center"
        },
        {
          "code": "medical_equipment_manufacturer",
          "label": "medical equipment manufacturer"
        },
        {
          "code": "medical_equipment_supplier",
          "label": "medical equipment supplier"
        },
        {
          "code": "medical_examiner",
          "label": "medical examiner"
        },
        {
          "code": "medical_group",
          "label": "medical group"
        },
        {
          "code": "medical_lab",
          "label": "medical laboratory"
        },
        {
          "code": "medical_office",
          "label": "medical office"
        },
        {
          "code": "medical_school",
          "label": "medical school"
        },
        {
          "code": "medical_spa",
          "label": "medical spa"
        },
        {
          "code": "medical_supply_store",
          "label": "medical supply store"
        },
        {
          "code": "medical_technology_manufacturer",
          "label": "medical technology manufacturer"
        },
        {
          "code": "medical_transcription_service",
          "label": "medical transcription service"
        },
        {
          "code": "medicine_exporter",
          "label": "medicine exporter"
        },
        {
          "code": "meditation_center",
          "label": "meditation center"
        },
        {
          "code": "meditation_instructor",
          "label": "meditation instructor"
        },
        {
          "code": "mediterranean_restaurant",
          "label": "mediterranean restaurant"
        },
        {
          "code": "meeting_planning_service",
          "label": "meeting planning service"
        },
        {
          "code": "mehandi_class",
          "label": "mehandi class"
        },
        {
          "code": "mehndi_designer",
          "label": "mehndi designer"
        },
        {
          "code": "memorial_estate",
          "label": "memorial estate"
        },
        {
          "code": "memorial_park",
          "label": "memorial park"
        },
        {
          "code": "mennonite_church",
          "label": "mennonite church"
        },
        {
          "code": "mens_clothing_store",
          "label": "men's clothing store"
        },
        {
          "code": "mens_tailor",
          "label": "mens tailor"
        },
        {
          "code": "mental_health_clinic",
          "label": "mental health clinic"
        },
        {
          "code": "mental_health_service",
          "label": "mental health service"
        },
        {
          "code": "mercantile_development",
          "label": "mercantile development"
        },
        {
          "code": "mercedes_benz_dealer",
          "label": "mercedes-benz dealer"
        },
        {
          "code": "messianic_synagogue",
          "label": "messianic synagogue"
        },
        {
          "code": "metal_construction_company",
          "label": "metal construction company"
        },
        {
          "code": "metal_detecting_equipment_supplier",
          "label": "metal detecting equipment supplier"
        },
        {
          "code": "metal_fabricator",
          "label": "metal fabricator"
        },
        {
          "code": "metal_finisher",
          "label": "metal finisher"
        },
        {
          "code": "metal_heat_treating_service",
          "label": "metal heat treating service"
        },
        {
          "code": "metal_industry_suppliers",
          "label": "metal industry suppliers"
        },
        {
          "code": "metal_machinery_supplier",
          "label": "metal machinery supplier"
        },
        {
          "code": "metal_polishing_service",
          "label": "metal polishing service"
        },
        {
          "code": "metal_processing_company",
          "label": "metal processing company"
        },
        {
          "code": "metal_stamping_service",
          "label": "metal stamping service"
        },
        {
          "code": "metal_supplier",
          "label": "metal supplier"
        },
        {
          "code": "metal_working_shop",
          "label": "metal working shop"
        },
        {
          "code": "metal_workshop",
          "label": "metal workshop"
        },
        {
          "code": "metallurgy_company",
          "label": "metallurgy company"
        },
        {
          "code": "metalware_dealer",
          "label": "metalware dealer"
        },
        {
          "code": "metalware_producer",
          "label": "metalware producer"
        },
        {
          "code": "metaphysical_supply_store",
          "label": "metaphysical supply store"
        },
        {
          "code": "methodist_church",
          "label": "methodist church"
        },
        {
          "code": "metropolitan_train_company",
          "label": "metropolitan train company"
        },
        {
          "code": "mexican_goods_store",
          "label": "mexican goods store"
        },
        {
          "code": "mexican_grocery_store",
          "label": "mexican grocery store"
        },
        {
          "code": "mexican_restaurant",
          "label": "mexican restaurant"
        },
        {
          "code": "mexican_torta_restaurant",
          "label": "mexican torta restaurant"
        },
        {
          "code": "mfr",
          "label": "mfr"
        },
        {
          "code": "microbiologist",
          "label": "microbiologist"
        },
        {
          "code": "microwave_oven_repair_service",
          "label": "microwave oven repair service"
        },
        {
          "code": "mid_atlantic_us_restaurant",
          "label": "mid-atlantic restaurant (us)"
        },
        {
          "code": "middle_eastern_restaurant",
          "label": "middle eastern restaurant"
        },
        {
          "code": "middle_school",
          "label": "middle school"
        },
        {
          "code": "midwife",
          "label": "midwife"
        },
        {
          "code": "militar_archive",
          "label": "military archive"
        },
        {
          "code": "militar_residence",
          "label": "military residence"
        },
        {
          "code": "military_barrack",
          "label": "military barracks"
        },
        {
          "code": "military_base",
          "label": "military base"
        },
        {
          "code": "military_board",
          "label": "military board"
        },
        {
          "code": "military_cemetery",
          "label": "military cemetery"
        },
        {
          "code": "military_hospital",
          "label": "military hospital"
        },
        {
          "code": "military_recruiting_office",
          "label": "military recruiting office"
        },
        {
          "code": "military_school",
          "label": "military school"
        },
        {
          "code": "military_town",
          "label": "military town"
        },
        {
          "code": "milk_delivery_service",
          "label": "milk delivery service"
        },
        {
          "code": "mill",
          "label": "mill"
        },
        {
          "code": "millwork_shop",
          "label": "millwork shop"
        },
        {
          "code": "mine",
          "label": "mine"
        },
        {
          "code": "mineral_water_company",
          "label": "mineral water company"
        },
        {
          "code": "mineral_water_wholesale",
          "label": "mineral water wholesale"
        },
        {
          "code": "mini_dealer",
          "label": "mini dealer"
        },
        {
          "code": "miniature_golf_course",
          "label": "miniature golf course"
        },
        {
          "code": "miniatures_store",
          "label": "miniatures store"
        },
        {
          "code": "minibus_taxi_service",
          "label": "minibus taxi service"
        },
        {
          "code": "mining_company",
          "label": "mining company"
        },
        {
          "code": "mining_consultant",
          "label": "mining consultant"
        },
        {
          "code": "mining_engineer",
          "label": "mining engineer"
        },
        {
          "code": "mining_equipment",
          "label": "mining equipment"
        },
        {
          "code": "ministry_of_education",
          "label": "ministry of education"
        },
        {
          "code": "mirror_shop",
          "label": "mirror shop"
        },
        {
          "code": "miso_cutlet_restaurant",
          "label": "miso cutlet restaurant"
        },
        {
          "code": "missing_persons_organization",
          "label": "missing persons organization"
        },
        {
          "code": "mission",
          "label": "mission"
        },
        {
          "code": "mitsubishi_dealer",
          "label": "mitsubishi dealer"
        },
        {
          "code": "mobile_catering",
          "label": "mobile caterer"
        },
        {
          "code": "mobile_disco",
          "label": "mobile disco"
        },
        {
          "code": "mobile_hairdresser",
          "label": "mobile hairdresser"
        },
        {
          "code": "mobile_home_dealer",
          "label": "mobile home dealer"
        },
        {
          "code": "mobile_home_park",
          "label": "mobile home park"
        },
        {
          "code": "mobile_home_rental_agency",
          "label": "mobile home rental agency"
        },
        {
          "code": "mobile_home_supply_store",
          "label": "mobile home supply store"
        },
        {
          "code": "mobile_money_agent",
          "label": "mobile money agent"
        },
        {
          "code": "mobile_network_operator",
          "label": "mobile network operator"
        },
        {
          "code": "mobile_phone_repair_shop",
          "label": "mobile phone repair shop"
        },
        {
          "code": "mobility_equipment_supplier",
          "label": "mobility equipment supplier"
        },
        {
          "code": "model_car_play_area",
          "label": "model car play area"
        },
        {
          "code": "model_design_company",
          "label": "model design company"
        },
        {
          "code": "model_portfolio_studio",
          "label": "model portfolio studio"
        },
        {
          "code": "model_train_store",
          "label": "model train store"
        },
        {
          "code": "modeling_agency",
          "label": "modeling agency"
        },
        {
          "code": "modeling_school",
          "label": "modeling school"
        },
        {
          "code": "modern_art_museum",
          "label": "modern art museum"
        },
        {
          "code": "modern_british_restaurant",
          "label": "modern british restaurant"
        },
        {
          "code": "modern_european_restaurant",
          "label": "modern european restaurant"
        },
        {
          "code": "modern_french_restaurant",
          "label": "modern french restaurant"
        },
        {
          "code": "modern_indian_restaurant",
          "label": "modern indian restaurant"
        },
        {
          "code": "modular_home_builder",
          "label": "modular home builder"
        },
        {
          "code": "modular_home_dealer",
          "label": "modular home dealer"
        },
        {
          "code": "mold_maker",
          "label": "mold maker"
        },
        {
          "code": "molding_supplier",
          "label": "molding supplier"
        },
        {
          "code": "monastery",
          "label": "monastery"
        },
        {
          "code": "money_order_service",
          "label": "money order service"
        },
        {
          "code": "money_transfer_service",
          "label": "money transfer service"
        },
        {
          "code": "mongolian_barbecue_restaurant",
          "label": "mongolian barbecue restaurant"
        },
        {
          "code": "monja_restaurant",
          "label": "monjayaki restaurant"
        },
        {
          "code": "monogramming_service",
          "label": "monogramming service"
        },
        {
          "code": "montessori_school",
          "label": "montessori school"
        },
        {
          "code": "monument_maker",
          "label": "monument maker"
        },
        {
          "code": "moped_dealer",
          "label": "moped dealer"
        },
        {
          "code": "moravian_church",
          "label": "moravian church"
        },
        {
          "code": "mordern_izakaya_restaurants",
          "label": "modern izakaya restaurants"
        },
        {
          "code": "moroccan_restaurant",
          "label": "moroccan restaurant"
        },
        {
          "code": "mortgage_broker",
          "label": "mortgage broker"
        },
        {
          "code": "mortgage_lender",
          "label": "mortgage lender"
        },
        {
          "code": "mortuary",
          "label": "mortuary"
        },
        {
          "code": "mosque",
          "label": "mosque"
        },
        {
          "code": "motel",
          "label": "motel"
        },
        {
          "code": "motor_scooter_dealer",
          "label": "motor scooter dealer"
        },
        {
          "code": "motor_scooter_repair_shop",
          "label": "motor scooter repair shop"
        },
        {
          "code": "motor_vehicle_dealer",
          "label": "motor vehicle dealer"
        },
        {
          "code": "motorcycle_dealer",
          "label": "motorcycle dealer"
        },
        {
          "code": "motorcycle_driving_school",
          "label": "motorcycle driving school"
        },
        {
          "code": "motorcycle_insurance_agency",
          "label": "motorcycle insurance agency"
        },
        {
          "code": "motorcycle_parts_store",
          "label": "motorcycle parts store"
        },
        {
          "code": "motorcycle_rental_agency",
          "label": "motorcycle rental agency"
        },
        {
          "code": "motorcycle_repair_shop",
          "label": "motorcycle repair shop"
        },
        {
          "code": "motorcycle_shop",
          "label": "motorcycle shop"
        },
        {
          "code": "motoring_club",
          "label": "motoring club"
        },
        {
          "code": "motorsports_store",
          "label": "motorsports store"
        },
        {
          "code": "mountain_cable_car",
          "label": "mountain cable car"
        },
        {
          "code": "mountain_hut",
          "label": "mountain cabin"
        },
        {
          "code": "mountaineering_class",
          "label": "mountaineering class"
        },
        {
          "code": "movie_rental_kiosk",
          "label": "movie rental kiosk"
        },
        {
          "code": "movie_rental_store",
          "label": "movie rental store"
        },
        {
          "code": "movie_studio",
          "label": "movie studio"
        },
        {
          "code": "movie_theater",
          "label": "movie theater"
        },
        {
          "code": "moving_and_storage_service",
          "label": "moving and storage service"
        },
        {
          "code": "moving_company",
          "label": "moving company"
        },
        {
          "code": "moving_supply_store",
          "label": "moving supply store"
        },
        {
          "code": "mri_center",
          "label": "mri center"
        },
        {
          "code": "muay_thai_boxing_gym",
          "label": "muay thai boxing gym"
        },
        {
          "code": "muffler_shop",
          "label": "muffler shop"
        },
        {
          "code": "mulch_supplier",
          "label": "mulch supplier"
        },
        {
          "code": "multimedia_and_electronic_book_publisher",
          "label": "multimedia and electronic book publisher"
        },
        {
          "code": "municipal_administration_office",
          "label": "municipal administration office"
        },
        {
          "code": "municipal_corporation",
          "label": "municipal corporation"
        },
        {
          "code": "municipal_department_agricultural_development",
          "label": "municipal department agricultural development"
        },
        {
          "code": "municipal_department_agriculture_food_supply",
          "label": "municipal department agriculture food supply"
        },
        {
          "code": "municipal_department_civil_defense",
          "label": "municipal department civil defense"
        },
        {
          "code": "municipal_department_communication",
          "label": "municipal department communication"
        },
        {
          "code": "municipal_department_finance",
          "label": "municipal department finance"
        },
        {
          "code": "municipal_department_housing_and_urban_development",
          "label": "municipal department housing and urban development"
        },
        {
          "code": "municipal_department_of_culture",
          "label": "municipal department of culture"
        },
        {
          "code": "municipal_department_of_sports",
          "label": "municipal department of sports"
        },
        {
          "code": "municipal_department_of_tourism",
          "label": "municipal department of tourism"
        },
        {
          "code": "municipal_department_science_technology",
          "label": "municipal department science technology"
        },
        {
          "code": "municipal_department_social_defense",
          "label": "municipal department social defense"
        },
        {
          "code": "municipal_guard",
          "label": "municipal guard"
        },
        {
          "code": "municipal_health_department",
          "label": "municipal health department"
        },
        {
          "code": "municipal_office_education",
          "label": "municipal office education"
        },
        {
          "code": "municipal_social_development",
          "label": "municipal social development"
        },
        {
          "code": "murtabak_restaurant",
          "label": "murtabak restaurant"
        },
        {
          "code": "museum",
          "label": "museum"
        },
        {
          "code": "museum_of_space_history",
          "label": "museum of space history"
        },
        {
          "code": "museum_of_zoology",
          "label": "museum of zoology"
        },
        {
          "code": "music_box_store",
          "label": "music box store"
        },
        {
          "code": "music_college",
          "label": "music college"
        },
        {
          "code": "music_conservatory",
          "label": "music conservatory"
        },
        {
          "code": "music_instructor",
          "label": "music instructor"
        },
        {
          "code": "music_management_and_promotion",
          "label": "music management and promotion"
        },
        {
          "code": "music_producer",
          "label": "music producer"
        },
        {
          "code": "music_publisher",
          "label": "music publisher"
        },
        {
          "code": "music_school",
          "label": "music school"
        },
        {
          "code": "music_store",
          "label": "music store"
        },
        {
          "code": "musical_club",
          "label": "musical club"
        },
        {
          "code": "musical_instrument_manufacturer",
          "label": "musical instrument manufacturer"
        },
        {
          "code": "musical_instrument_rental_service",
          "label": "musical instrument rental service"
        },
        {
          "code": "musical_instrument_repair_shop",
          "label": "musical instrument repair shop"
        },
        {
          "code": "musical_instrument_store",
          "label": "musical instrument store"
        },
        {
          "code": "musician",
          "label": "musician"
        },
        {
          "code": "mutton_barbecue_restaurant",
          "label": "mutton barbecue restaurant"
        },
        {
          "code": "nail_salon",
          "label": "nail salon"
        },
        {
          "code": "nanotechnology_engineer",
          "label": "nanotechnology engineer"
        },
        {
          "code": "nasi_goreng_restaurant",
          "label": "nasi goreng restaurant"
        },
        {
          "code": "nasi_uduk_restaurant",
          "label": "nasi uduk restaurant"
        },
        {
          "code": "national_forest",
          "label": "national forest"
        },
        {
          "code": "national_health_foundation",
          "label": "national health foundation"
        },
        {
          "code": "national_library",
          "label": "national library"
        },
        {
          "code": "national_museum",
          "label": "national museum"
        },
        {
          "code": "national_park",
          "label": "national park"
        },
        {
          "code": "national_reserve",
          "label": "national reserve"
        },
        {
          "code": "native_american_goods_store",
          "label": "native american goods store"
        },
        {
          "code": "native_american_restaurant",
          "label": "native american restaurant"
        },
        {
          "code": "natural_foods_store",
          "label": "natural goods store"
        },
        {
          "code": "natural_history_museum",
          "label": "natural history museum"
        },
        {
          "code": "natural_stone_exporter",
          "label": "natural stone exporter"
        },
        {
          "code": "natural_stone_supplier",
          "label": "natural stone supplier"
        },
        {
          "code": "natural_stone_wholesaler",
          "label": "natural stone wholesaler"
        },
        {
          "code": "nature_preserve",
          "label": "nature preserve"
        },
        {
          "code": "naturopathic_practitioner",
          "label": "naturopathic practitioner"
        },
        {
          "code": "naval_base",
          "label": "naval base"
        },
        {
          "code": "navarraise_restaurant",
          "label": "navarraise restaurant"
        },
        {
          "code": "neapolitan_restaurant",
          "label": "neapolitan restaurant"
        },
        {
          "code": "needlework_shop",
          "label": "needlework shop"
        },
        {
          "code": "neon_sign_shop",
          "label": "neon sign shop"
        },
        {
          "code": "neonatal_physician",
          "label": "neonatal physician"
        },
        {
          "code": "nepalese_restaurant",
          "label": "nepalese restaurant"
        },
        {
          "code": "nephrologist",
          "label": "nephrologist"
        },
        {
          "code": "netball_club",
          "label": "netball club"
        },
        {
          "code": "neurologist",
          "label": "neurologist"
        },
        {
          "code": "neurosurgeon",
          "label": "neurosurgeon"
        },
        {
          "code": "new_age_church",
          "label": "new age church"
        },
        {
          "code": "new_england_restaurant",
          "label": "new england restaurant"
        },
        {
          "code": "new_us_american_restaurant",
          "label": "new american restaurant"
        },
        {
          "code": "new_years_tree_market",
          "label": "new years tree market"
        },
        {
          "code": "new_zealand_restaurant",
          "label": "new zealand restaurant"
        },
        {
          "code": "news_service",
          "label": "news service"
        },
        {
          "code": "newspaper_advertising_department",
          "label": "newspaper advertising department"
        },
        {
          "code": "newspaper_distribution",
          "label": "newspaper distribution"
        },
        {
          "code": "newspaper_publisher",
          "label": "newspaper publisher"
        },
        {
          "code": "newsstand",
          "label": "newsstand"
        },
        {
          "code": "nicaraguan_restaurant",
          "label": "nicaraguan restaurant"
        },
        {
          "code": "night_club",
          "label": "night club"
        },
        {
          "code": "night_market",
          "label": "night market"
        },
        {
          "code": "nissan_dealer",
          "label": "nissan dealer"
        },
        {
          "code": "non_denominational_church",
          "label": "non-denominational church"
        },
        {
          "code": "non_governmental_organization",
          "label": "non-governmental organization"
        },
        {
          "code": "non_profit_organization",
          "label": "non-profit organization"
        },
        {
          "code": "non_smoking_holiday_home",
          "label": "non smoking holiday home"
        },
        {
          "code": "noodle_shop",
          "label": "noodle shop"
        },
        {
          "code": "north_african_restaurant",
          "label": "north african restaurant"
        },
        {
          "code": "north_eastern_indian_restaurant",
          "label": "north eastern indian restaurant"
        },
        {
          "code": "northern_italian_restaurant",
          "label": "northern italian restaurant"
        },
        {
          "code": "norwegian_restaurant",
          "label": "norwegian restaurant"
        },
        {
          "code": "notaries_association",
          "label": "notaries association"
        },
        {
          "code": "notary_public",
          "label": "notary public"
        },
        {
          "code": "notions_store",
          "label": "notions store"
        },
        {
          "code": "novelties_wholesaler",
          "label": "novelties wholesaler"
        },
        {
          "code": "novelty_store",
          "label": "novelty store"
        },
        {
          "code": "nuclear_engineer",
          "label": "nuclear engineer"
        },
        {
          "code": "nuclear_power_company",
          "label": "nuclear power company"
        },
        {
          "code": "nuclear_power_plant",
          "label": "nuclear power plant"
        },
        {
          "code": "nudist_club",
          "label": "nudist club"
        },
        {
          "code": "nudist_park",
          "label": "nudist park"
        },
        {
          "code": "nuevo_latino_restaurant",
          "label": "nuevo latino restaurant"
        },
        {
          "code": "numerologist",
          "label": "numerologist"
        },
        {
          "code": "nunnery",
          "label": "convent"
        },
        {
          "code": "nurse_practitioner",
          "label": "nurse practitioner"
        },
        {
          "code": "nursery_school",
          "label": "nursery school"
        },
        {
          "code": "nursing_agency",
          "label": "nursing agency"
        },
        {
          "code": "nursing_association",
          "label": "nursing association"
        },
        {
          "code": "nursing_home",
          "label": "nursing home"
        },
        {
          "code": "nursing_school",
          "label": "nursing school"
        },
        {
          "code": "nut_store",
          "label": "nut store"
        },
        {
          "code": "nutritionist",
          "label": "nutritionist"
        },
        {
          "code": "nyonya_restaurant",
          "label": "nyonya restaurant"
        },
        {
          "code": "oaxacan_restaurant",
          "label": "oaxacan restaurant"
        },
        {
          "code": "obanzai_cuisine",
          "label": "obanzai restaurant"
        },
        {
          "code": "observation_deck",
          "label": "observation deck"
        },
        {
          "code": "observatory",
          "label": "observatory"
        },
        {
          "code": "obstetrics_gynecology_clinic",
          "label": "women's health clinic"
        },
        {
          "code": "occupational_health_service",
          "label": "occupational health service"
        },
        {
          "code": "occupational_medical_physician",
          "label": "occupational medical physician"
        },
        {
          "code": "occupational_safety_and_health",
          "label": "occupational safety and health"
        },
        {
          "code": "occupational_therapist",
          "label": "occupational therapist"
        },
        {
          "code": "oden_restaurant",
          "label": "oden restaurant"
        },
        {
          "code": "off_road_race_track",
          "label": "off-road race track"
        },
        {
          "code": "off_roading_area",
          "label": "off roading area"
        },
        {
          "code": "off_track_betting_shop",
          "label": "off track betting shop"
        },
        {
          "code": "offal_pot_cooking",
          "label": "offal pot cooking restaurant"
        },
        {
          "code": "office_accessories_wholesaler",
          "label": "office accessories wholesaler"
        },
        {
          "code": "office_equipment_rental_service",
          "label": "office equipment rental service"
        },
        {
          "code": "office_equipment_repair_service",
          "label": "office equipment repair service"
        },
        {
          "code": "office_equipment_supplier",
          "label": "office equipment supplier"
        },
        {
          "code": "office_furniture_store",
          "label": "office furniture store"
        },
        {
          "code": "office_of_vital_records",
          "label": "office of vital records"
        },
        {
          "code": "office_refurbishment_service",
          "label": "office refurbishment service"
        },
        {
          "code": "office_space_rental_agency",
          "label": "office space rental agency"
        },
        {
          "code": "office_supply_store",
          "label": "office supply store"
        },
        {
          "code": "office_supply_wholesaler",
          "label": "office supply wholesaler"
        },
        {
          "code": "oil_and_gas_exploration_service",
          "label": "oil and gas exploration service"
        },
        {
          "code": "oil_change_service",
          "label": "oil change service"
        },
        {
          "code": "oil_company",
          "label": "oil & natural gas company"
        },
        {
          "code": "oil_field_equipment_supplier",
          "label": "oil field equipment supplier"
        },
        {
          "code": "oil_refinery",
          "label": "oil refinery"
        },
        {
          "code": "oil_store",
          "label": "oil store"
        },
        {
          "code": "oil_wholesaler",
          "label": "oil wholesaler"
        },
        {
          "code": "oilfield",
          "label": "oilfield"
        },
        {
          "code": "okonomiyaki_restaurant",
          "label": "okonomiyaki restaurant"
        },
        {
          "code": "oldsmobile_dealer",
          "label": "oldsmobile dealer"
        },
        {
          "code": "olive_oil_bottling_company",
          "label": "olive oil bottling company"
        },
        {
          "code": "olive_oil_cooperative",
          "label": "olive oil cooperative"
        },
        {
          "code": "olive_oil_manufacturer",
          "label": "olive oil manufacturer"
        },
        {
          "code": "oncologist",
          "label": "oncologist"
        },
        {
          "code": "opel_dealer",
          "label": "opel dealer"
        },
        {
          "code": "open_air_museum",
          "label": "open air museum"
        },
        {
          "code": "open_university",
          "label": "open university"
        },
        {
          "code": "opera_company",
          "label": "opera company"
        },
        {
          "code": "opera_house",
          "label": "opera house"
        },
        {
          "code": "ophthalmologist",
          "label": "ophthalmologist"
        },
        {
          "code": "ophthalmology_clinic",
          "label": "ophthalmology clinic"
        },
        {
          "code": "optical_products_manufacturer",
          "label": "optical products manufacturer"
        },
        {
          "code": "optical_wholesaler",
          "label": "optical wholesaler"
        },
        {
          "code": "optician",
          "label": "optician"
        },
        {
          "code": "optometrist",
          "label": "optometrist"
        },
        {
          "code": "oral_maxillofacial_surgeon",
          "label": "oral maxillofacial surgeon"
        },
        {
          "code": "oral_surgeon",
          "label": "oral surgeon"
        },
        {
          "code": "orchard",
          "label": "orchard"
        },
        {
          "code": "orchestra",
          "label": "orchestra"
        },
        {
          "code": "orchid_farm",
          "label": "orchid farm"
        },
        {
          "code": "orchid_grower",
          "label": "orchid grower"
        },
        {
          "code": "organ_donation_and_tissue_bank",
          "label": "organ donation and tissue bank"
        },
        {
          "code": "organic_drug_store",
          "label": "organic drug store"
        },
        {
          "code": "organic_farm",
          "label": "organic farm"
        },
        {
          "code": "organic_food_store",
          "label": "organic food store"
        },
        {
          "code": "organic_restaurant",
          "label": "organic restaurant"
        },
        {
          "code": "organic_store",
          "label": "organic shop"
        },
        {
          "code": "oriental_goods_store",
          "label": "oriental goods store"
        },
        {
          "code": "oriental_medicine_clinic",
          "label": "oriental medicine clinic"
        },
        {
          "code": "oriental_medicine_store",
          "label": "oriental medicine store"
        },
        {
          "code": "oriental_rug_store",
          "label": "oriental rug store"
        },
        {
          "code": "orphan_asylum",
          "label": "orphan asylum"
        },
        {
          "code": "orphanage",
          "label": "orphanage"
        },
        {
          "code": "orthodontist",
          "label": "orthodontist"
        },
        {
          "code": "orthodox_church",
          "label": "orthodox church"
        },
        {
          "code": "orthodox_synagogue",
          "label": "orthodox synagogue"
        },
        {
          "code": "orthopedic_clinic",
          "label": "orthopedic clinic"
        },
        {
          "code": "orthopedic_shoe_store",
          "label": "orthopedic shoe store"
        },
        {
          "code": "orthopedic_surgeon",
          "label": "orthopedic surgeon"
        },
        {
          "code": "orthoptist",
          "label": "orthoptist"
        },
        {
          "code": "orthotics_and_prosthetics_service",
          "label": "orthotics & prosthetics service"
        },
        {
          "code": "osteopath",
          "label": "osteopath"
        },
        {
          "code": "otolaryngologist",
          "label": "otolaryngologist"
        },
        {
          "code": "otolaryngology_clinic",
          "label": "otolaryngology clinic"
        },
        {
          "code": "outboard_motor_store",
          "label": "outboard motor store"
        },
        {
          "code": "outdoor_activity_organizer",
          "label": "outdoor activity organiser"
        },
        {
          "code": "outdoor_bath",
          "label": "outdoor bath"
        },
        {
          "code": "outdoor_clothing_and_equipment_shop",
          "label": "outdoor clothing and equipment shop"
        },
        {
          "code": "outdoor_equestrian_facility",
          "label": "outdoor equestrian facility"
        },
        {
          "code": "outdoor_furniture_store",
          "label": "outdoor furniture store"
        },
        {
          "code": "outdoor_movie_theatre",
          "label": "outdoor movie theater"
        },
        {
          "code": "outdoor_sports_store",
          "label": "outdoor sports store"
        },
        {
          "code": "outdoor_swimming_pool",
          "label": "outdoor swimming pool"
        },
        {
          "code": "outerwear_store",
          "label": "outerwear store"
        },
        {
          "code": "outlet_mall",
          "label": "outlet mall"
        },
        {
          "code": "outlet_store",
          "label": "outlet store"
        },
        {
          "code": "oxygen_cocktail_spot",
          "label": "oxygen cocktail spot"
        },
        {
          "code": "oxygen_equipment_supplier",
          "label": "oxygen equipment supplier"
        },
        {
          "code": "oyster_bar_restaurant",
          "label": "oyster bar restaurant"
        },
        {
          "code": "oyster_supplier",
          "label": "oyster supplier"
        },
        {
          "code": "pachinko",
          "label": "pachinko parlor"
        },
        {
          "code": "pacific_rim_restaurant",
          "label": "pacific rim restaurant"
        },
        {
          "code": "package_locker",
          "label": "package locker"
        },
        {
          "code": "packaging_company",
          "label": "packaging company"
        },
        {
          "code": "packaging_machinery",
          "label": "packaging machinery"
        },
        {
          "code": "packaging_supply_store",
          "label": "packaging supply store"
        },
        {
          "code": "padang_restaurant",
          "label": "padang restaurant"
        },
        {
          "code": "padel_club",
          "label": "padel club"
        },
        {
          "code": "padel_court",
          "label": "padel court"
        },
        {
          "code": "pagoda",
          "label": "pagoda"
        },
        {
          "code": "pain_control_clinic",
          "label": "pain control clinic"
        },
        {
          "code": "pain_management_physician",
          "label": "pain management physician"
        },
        {
          "code": "paint_manufacturer",
          "label": "paint manufacturer"
        },
        {
          "code": "paint_store",
          "label": "paint store"
        },
        {
          "code": "paint_stripping_company",
          "label": "paint stripping company"
        },
        {
          "code": "paintball_center",
          "label": "paintball center"
        },
        {
          "code": "paintball_store",
          "label": "paintball store"
        },
        {
          "code": "painter",
          "label": "painter"
        },
        {
          "code": "painting",
          "label": "painting"
        },
        {
          "code": "painting_lessons",
          "label": "painting lessons"
        },
        {
          "code": "painting_studio",
          "label": "painting studio"
        },
        {
          "code": "paintings_store",
          "label": "paintings store"
        },
        {
          "code": "pakistani_restaurant",
          "label": "pakistani restaurant"
        },
        {
          "code": "pallet_supplier",
          "label": "pallet supplier"
        },
        {
          "code": "pan_asian_restaurant",
          "label": "pan-asian restaurant"
        },
        {
          "code": "pan_latin_restaurant",
          "label": "pan-latin restaurant"
        },
        {
          "code": "pancake_house",
          "label": "pancake restaurant"
        },
        {
          "code": "paper_bag_supplier",
          "label": "paper bag supplier"
        },
        {
          "code": "paper_distributor",
          "label": "paper distributor"
        },
        {
          "code": "paper_exporter",
          "label": "paper exporter"
        },
        {
          "code": "paper_mill",
          "label": "paper mill"
        },
        {
          "code": "paper_shredding_machine_supplier",
          "label": "paper shredding machine supplier"
        },
        {
          "code": "paper_store",
          "label": "paper store"
        },
        {
          "code": "paraguayan_restaurant",
          "label": "paraguayan restaurant"
        },
        {
          "code": "paralegal_services_provider",
          "label": "paralegal services provider"
        },
        {
          "code": "parasailing_ride_service",
          "label": "parasailing ride service"
        },
        {
          "code": "parish",
          "label": "parish"
        },
        {
          "code": "park",
          "label": "park"
        },
        {
          "code": "park_and_ride",
          "label": "park & ride"
        },
        {
          "code": "parking_garage",
          "label": "parking garage"
        },
        {
          "code": "parking_lot",
          "label": "parking lot"
        },
        {
          "code": "parking_lot_for_bicycles",
          "label": "parking lot for bicycles"
        },
        {
          "code": "parking_lot_for_motorcycle",
          "label": "parking lot for motorcycles"
        },
        {
          "code": "parkour_spot",
          "label": "parkour spot"
        },
        {
          "code": "parochial_school",
          "label": "parochial school"
        },
        {
          "code": "parsi_restaurant",
          "label": "parsi restaurant"
        },
        {
          "code": "parsi_temple",
          "label": "parsi temple"
        },
        {
          "code": "part_time_daycare",
          "label": "part time daycare"
        },
        {
          "code": "party_equipment_rental_service",
          "label": "party equipment rental service"
        },
        {
          "code": "party_planner",
          "label": "party planner"
        },
        {
          "code": "party_store",
          "label": "party store"
        },
        {
          "code": "passport_agent",
          "label": "passport agent"
        },
        {
          "code": "passport_office",
          "label": "passport office"
        },
        {
          "code": "passport_photo_processor",
          "label": "passport photo processor"
        },
        {
          "code": "pasta_shop",
          "label": "pasta shop"
        },
        {
          "code": "pastry_shop",
          "label": "pastry shop"
        },
        {
          "code": "patent_attorney",
          "label": "patent attorney"
        },
        {
          "code": "patent_office",
          "label": "patent office"
        },
        {
          "code": "paternity_testing_service",
          "label": "paternity testing service"
        },
        {
          "code": "pathologist",
          "label": "pathologist"
        },
        {
          "code": "patients_support_association",
          "label": "patients support association"
        },
        {
          "code": "patio_enclosure_supplier",
          "label": "patio enclosure supplier"
        },
        {
          "code": "patisserie",
          "label": "patisserie"
        },
        {
          "code": "paving_contractor",
          "label": "paving contractor"
        },
        {
          "code": "paving_materials_supplier",
          "label": "paving materials supplier"
        },
        {
          "code": "pawn_shop",
          "label": "pawn shop"
        },
        {
          "code": "payroll_service",
          "label": "payroll service"
        },
        {
          "code": "pecel_lele_restaurant",
          "label": "pecel lele restaurant"
        },
        {
          "code": "pedestrian_zone",
          "label": "pedestrian zone"
        },
        {
          "code": "pediatric_cardiologist",
          "label": "pediatric cardiologist"
        },
        {
          "code": "pediatric_dentist",
          "label": "pediatric dentist"
        },
        {
          "code": "pediatric_ophthalmologist",
          "label": "pediatric ophthalmologist"
        },
        {
          "code": "pediatrician",
          "label": "pediatrician"
        },
        {
          "code": "pempek_restaurant",
          "label": "pempek restaurant"
        },
        {
          "code": "pen_store",
          "label": "pen store"
        },
        {
          "code": "pennsylvania_dutch_restaurant",
          "label": "pennsylvania dutch restaurant"
        },
        {
          "code": "pension_office",
          "label": "pension office"
        },
        {
          "code": "pentecostal_church",
          "label": "pentecostal church"
        },
        {
          "code": "performing_arts_group",
          "label": "performing arts group"
        },
        {
          "code": "performing_arts_theater",
          "label": "performing arts theater"
        },
        {
          "code": "perfume_store",
          "label": "perfume store"
        },
        {
          "code": "perinatal_center",
          "label": "perinatal center"
        },
        {
          "code": "periodontist",
          "label": "periodontist"
        },
        {
          "code": "permanent_make_up_clinic",
          "label": "permanent make-up clinic"
        },
        {
          "code": "persian_restaurant",
          "label": "persian restaurant"
        },
        {
          "code": "personal_injury_lawyer",
          "label": "personal injury attorney"
        },
        {
          "code": "personal_trainer",
          "label": "personal trainer"
        },
        {
          "code": "peruvian_restaurant",
          "label": "peruvian restaurant"
        },
        {
          "code": "pest_control_service",
          "label": "pest control service"
        },
        {
          "code": "pet_adoption_service",
          "label": "pet adoption service"
        },
        {
          "code": "pet_boarding_service",
          "label": "pet boarding service"
        },
        {
          "code": "pet_cemetery",
          "label": "pet cemetery"
        },
        {
          "code": "pet_friendly_accommodation",
          "label": "pet friendly accommodation"
        },
        {
          "code": "pet_funeral_services",
          "label": "pet funeral service"
        },
        {
          "code": "pet_groomer",
          "label": "pet groomer"
        },
        {
          "code": "pet_moving_service",
          "label": "pet moving service"
        },
        {
          "code": "pet_sitter",
          "label": "pet sitter"
        },
        {
          "code": "pet_store",
          "label": "pet store"
        },
        {
          "code": "pet_supply_store",
          "label": "pet supply store"
        },
        {
          "code": "pet_trainer",
          "label": "pet trainer"
        },
        {
          "code": "petrochemical_engineer",
          "label": "petrochemical engineer"
        },
        {
          "code": "petroleum_products_company",
          "label": "petroleum products company"
        },
        {
          "code": "peugeot_dealer",
          "label": "peugeot dealer"
        },
        {
          "code": "pharmaceutical_company",
          "label": "pharmaceutical company"
        },
        {
          "code": "pharmaceutical_lab",
          "label": "pharmaceutical lab"
        },
        {
          "code": "pharmaceutical_products_wholesaler",
          "label": "pharmaceutical products wholesaler"
        },
        {
          "code": "pharmacy",
          "label": "pharmacy"
        },
        {
          "code": "philharmonic_hall",
          "label": "philharmonic hall"
        },
        {
          "code": "pho_restaurant",
          "label": "pho restaurant"
        },
        {
          "code": "phone_repair_service",
          "label": "phone repair service"
        },
        {
          "code": "photo_agency",
          "label": "photo agency"
        },
        {
          "code": "photo_booth",
          "label": "photo booth"
        },
        {
          "code": "photo_lab",
          "label": "photo lab"
        },
        {
          "code": "photo_restoration_service",
          "label": "photo restoration service"
        },
        {
          "code": "photo_shop",
          "label": "photo shop"
        },
        {
          "code": "photocopiers_supplier",
          "label": "photocopiers supplier"
        },
        {
          "code": "photographer",
          "label": "photographer"
        },
        {
          "code": "photography_class",
          "label": "photography class"
        },
        {
          "code": "photography_school",
          "label": "photography school"
        },
        {
          "code": "photography_service",
          "label": "photography service"
        },
        {
          "code": "photography_studio",
          "label": "photography studio"
        },
        {
          "code": "physiatrist",
          "label": "physiatrist"
        },
        {
          "code": "physical_examination_center",
          "label": "physical examination center"
        },
        {
          "code": "physical_fitness_program",
          "label": "physical fitness program"
        },
        {
          "code": "physician_referral_service",
          "label": "physician referral service"
        },
        {
          "code": "physiotherapist",
          "label": "physical therapist"
        },
        {
          "code": "physiotherapy_center",
          "label": "physical therapy clinic"
        },
        {
          "code": "physiotherapy_equip_supplier",
          "label": "physiotherapy equipment supplier"
        },
        {
          "code": "piano_bar",
          "label": "piano bar"
        },
        {
          "code": "piano_instructor",
          "label": "piano instructor"
        },
        {
          "code": "piano_maker",
          "label": "piano maker"
        },
        {
          "code": "piano_moving_service",
          "label": "piano moving service"
        },
        {
          "code": "piano_repair_service",
          "label": "piano repair service"
        },
        {
          "code": "piano_store",
          "label": "piano store"
        },
        {
          "code": "piano_tuning_service",
          "label": "piano tuning service"
        },
        {
          "code": "pick_your_own_farm_produce",
          "label": "pick your own farm produce"
        },
        {
          "code": "picnic_ground",
          "label": "picnic ground"
        },
        {
          "code": "picture_frame_shop",
          "label": "picture frame shop"
        },
        {
          "code": "pie_shop",
          "label": "pie shop"
        },
        {
          "code": "piedmontese_restaurant",
          "label": "piedmontese restaurant"
        },
        {
          "code": "pilates_studio",
          "label": "pilates studio"
        },
        {
          "code": "pile_driver",
          "label": "pile driver"
        },
        {
          "code": "pilgrimages_place",
          "label": "pilgrimage place"
        },
        {
          "code": "pinatas_supplier",
          "label": "pinatas supplier"
        },
        {
          "code": "pinball_machine_supplier",
          "label": "pinball machine supplier"
        },
        {
          "code": "pine_furniture_shop",
          "label": "pine furniture shop"
        },
        {
          "code": "pipe_supplier",
          "label": "pipe supplier"
        },
        {
          "code": "pizza_delivery_service",
          "label": "pizza delivery"
        },
        {
          "code": "pizza_restaurant",
          "label": "pizza restaurant"
        },
        {
          "code": "pizzatakeaway",
          "label": "pizza takeaway"
        },
        {
          "code": "place_of_worship",
          "label": "place of worship"
        },
        {
          "code": "planetarium",
          "label": "planetarium"
        },
        {
          "code": "plant_and_machinery_hire",
          "label": "plant and machinery hire"
        },
        {
          "code": "plant_nursery",
          "label": "plant nursery"
        },
        {
          "code": "plast_window_store",
          "label": "plast window store"
        },
        {
          "code": "plaster_contractor",
          "label": "plasterer"
        },
        {
          "code": "plastic_bag_supplier",
          "label": "plastic bag supplier"
        },
        {
          "code": "plastic_bags_wholesaler",
          "label": "plastic bags wholesaler"
        },
        {
          "code": "plastic_fabrication_company",
          "label": "plastic fabrication company"
        },
        {
          "code": "plastic_injection_molding_service",
          "label": "plastic injection molding service"
        },
        {
          "code": "plastic_products_supplier",
          "label": "plastic products supplier"
        },
        {
          "code": "plastic_resin_manufacturer",
          "label": "plastic resin manufacturer"
        },
        {
          "code": "plastic_surgeon",
          "label": "plastic surgeon"
        },
        {
          "code": "plastic_surgery_clinic",
          "label": "plastic surgery clinic"
        },
        {
          "code": "plastic_wholesaler",
          "label": "plastic wholesaler"
        },
        {
          "code": "plating_service",
          "label": "plating service"
        },
        {
          "code": "play_school",
          "label": "play school"
        },
        {
          "code": "playground",
          "label": "playground"
        },
        {
          "code": "playground_equipment_supplier",
          "label": "playground equipment supplier"
        },
        {
          "code": "playgroup",
          "label": "playgroup"
        },
        {
          "code": "plumber",
          "label": "plumber"
        },
        {
          "code": "plumbing_supply_store",
          "label": "plumbing supply store"
        },
        {
          "code": "plus_size_clothing_store",
          "label": "plus size clothing store"
        },
        {
          "code": "plywood_supplier",
          "label": "plywood supplier"
        },
        {
          "code": "pneumatic_tools_supplier",
          "label": "pneumatic tools supplier"
        },
        {
          "code": "po_boys_restaurant",
          "label": "po� boys restaurant"
        },
        {
          "code": "podiatrist",
          "label": "podiatrist"
        },
        {
          "code": "police_academy",
          "label": "police academy"
        },
        {
          "code": "police_supply_store",
          "label": "police supply store"
        },
        {
          "code": "polish_restaurant",
          "label": "polish restaurant"
        },
        {
          "code": "political_party",
          "label": "political party"
        },
        {
          "code": "polo_club",
          "label": "polo club"
        },
        {
          "code": "polygraph_service",
          "label": "polygraph service"
        },
        {
          "code": "polymer_supplier",
          "label": "polymer supplier"
        },
        {
          "code": "polynesian_restaurant",
          "label": "polynesian restaurant"
        },
        {
          "code": "polytechnic_school",
          "label": "polytechnic"
        },
        {
          "code": "polythene_and_plastic_sheeting_supplier",
          "label": "polythene and plastic sheeting supplier"
        },
        {
          "code": "pond_contractor",
          "label": "pond contractor"
        },
        {
          "code": "pond_fish_supplier",
          "label": "pond fish supplier"
        },
        {
          "code": "pond_supply_store",
          "label": "pond supply store"
        },
        {
          "code": "pontiac_dealer",
          "label": "pontiac dealer"
        },
        {
          "code": "pony_club",
          "label": "pony club"
        },
        {
          "code": "pony_ride_service",
          "label": "pony ride service"
        },
        {
          "code": "pool_academy",
          "label": "pool academy"
        },
        {
          "code": "pool_billard_club",
          "label": "pool billard club"
        },
        {
          "code": "pool_cleaning_service",
          "label": "pool cleaning service"
        },
        {
          "code": "pool_hall",
          "label": "pool hall"
        },
        {
          "code": "popcorn_store",
          "label": "popcorn store"
        },
        {
          "code": "pork_cutlet_rice_bowl_restaurant",
          "label": "katsudon restaurant"
        },
        {
          "code": "porridge_restaurant",
          "label": "porridge restaurant"
        },
        {
          "code": "porsche_dealer",
          "label": "porsche dealer"
        },
        {
          "code": "port_authority",
          "label": "port authority"
        },
        {
          "code": "port_operating_company",
          "label": "port operating company"
        },
        {
          "code": "portable_building_manufacturer",
          "label": "portable building manufacturer"
        },
        {
          "code": "portable_toilet_supplier",
          "label": "portable toilet supplier"
        },
        {
          "code": "portrait_studio",
          "label": "portrait studio"
        },
        {
          "code": "portuguese_restaurant",
          "label": "portuguese restaurant"
        },
        {
          "code": "post_office",
          "label": "post office"
        },
        {
          "code": "poster_store",
          "label": "poster store"
        },
        {
          "code": "pottery_classes",
          "label": "pottery classes"
        },
        {
          "code": "pottery_manufacturer",
          "label": "pottery manufacturer"
        },
        {
          "code": "pottery_store",
          "label": "pottery store"
        },
        {
          "code": "poultry_farm",
          "label": "poultry farm"
        },
        {
          "code": "poultry_store",
          "label": "poultry store"
        },
        {
          "code": "powder_coating_service",
          "label": "powder coating service"
        },
        {
          "code": "power_plant",
          "label": "power station"
        },
        {
          "code": "power_plant_consultant",
          "label": "power plant consultant"
        },
        {
          "code": "power_plant_equipment_supplier",
          "label": "power plant equipment supplier"
        },
        {
          "code": "pozole_restaurant",
          "label": "pozole restaurant"
        },
        {
          "code": "prawn_fishing",
          "label": "prawn fishing"
        },
        {
          "code": "pre_gymnasium_school",
          "label": "pre gymnasium school"
        },
        {
          "code": "precision_engineer",
          "label": "precision engineer"
        },
        {
          "code": "prefabricated_house_companies",
          "label": "prefabricated house companies"
        },
        {
          "code": "prefecture",
          "label": "prefecture"
        },
        {
          "code": "prefecture_government_office",
          "label": "japanese prefecture government office"
        },
        {
          "code": "pregnancy_care_center",
          "label": "pregnancy care center"
        },
        {
          "code": "preparatory_school",
          "label": "preparatory school"
        },
        {
          "code": "presbyterian_church",
          "label": "presbyterian church"
        },
        {
          "code": "preschool",
          "label": "preschool"
        },
        {
          "code": "press_advisory",
          "label": "press advisory"
        },
        {
          "code": "pressure_washing_service",
          "label": "pressure washing service"
        },
        {
          "code": "pretzel_store",
          "label": "pretzel store"
        },
        {
          "code": "priest",
          "label": "priest"
        },
        {
          "code": "primary_school",
          "label": "primary school"
        },
        {
          "code": "print_shop",
          "label": "print shop"
        },
        {
          "code": "printed_music_publisher",
          "label": "printed music publisher"
        },
        {
          "code": "printer_ink_refill_store",
          "label": "printer ink refill store"
        },
        {
          "code": "printer_repair_service",
          "label": "printer repair service"
        },
        {
          "code": "printing_equipment_and_supplies",
          "label": "printing equipment and supplies"
        },
        {
          "code": "printing_equipment_supplier",
          "label": "printing equipment supplier"
        },
        {
          "code": "prison",
          "label": "prison"
        },
        {
          "code": "private_college",
          "label": "private college"
        },
        {
          "code": "private_equity_firm",
          "label": "private equity firm"
        },
        {
          "code": "private_golf_course",
          "label": "private golf course"
        },
        {
          "code": "private_guest_room",
          "label": "homestay"
        },
        {
          "code": "private_hospital",
          "label": "private hospital"
        },
        {
          "code": "private_investigator",
          "label": "private investigator"
        },
        {
          "code": "private_school",
          "label": "private school"
        },
        {
          "code": "private_sector_bank",
          "label": "private sector bank"
        },
        {
          "code": "private_tutor",
          "label": "private tutor"
        },
        {
          "code": "private_university",
          "label": "private university"
        },
        {
          "code": "probation_office",
          "label": "probation office"
        },
        {
          "code": "process_server",
          "label": "process server"
        },
        {
          "code": "proctologist",
          "label": "proctologist"
        },
        {
          "code": "produce_market",
          "label": "produce market"
        },
        {
          "code": "produce_wholesaler",
          "label": "produce wholesaler"
        },
        {
          "code": "producteur_de_foie_gras",
          "label": "foie gras producer"
        },
        {
          "code": "professional_and_hobby_associations",
          "label": "professional and hobby associations"
        },
        {
          "code": "professional_organizer",
          "label": "professional organizer"
        },
        {
          "code": "promenade",
          "label": "promenade"
        },
        {
          "code": "promotional_products_supplier",
          "label": "promotional products supplier"
        },
        {
          "code": "propane_supplier",
          "label": "propane supplier"
        },
        {
          "code": "propeller_shop",
          "label": "propeller shop"
        },
        {
          "code": "property_administrator",
          "label": "property administrator"
        },
        {
          "code": "property_investment",
          "label": "property investment"
        },
        {
          "code": "property_maintenance",
          "label": "property maintenance"
        },
        {
          "code": "property_management_company",
          "label": "property management company"
        },
        {
          "code": "property_registry",
          "label": "land registry office"
        },
        {
          "code": "prosthetics",
          "label": "prosthetics"
        },
        {
          "code": "prosthodontist",
          "label": "prosthodontist"
        },
        {
          "code": "protective_clothing_supplier",
          "label": "protective clothing supplier"
        },
        {
          "code": "protestant_church",
          "label": "protestant church"
        },
        {
          "code": "provence_restaurant",
          "label": "provence restaurant"
        },
        {
          "code": "provincial_council",
          "label": "provincial council"
        },
        {
          "code": "psychiatric_hospital",
          "label": "psychiatric hospital"
        },
        {
          "code": "psychiatrist",
          "label": "psychiatrist"
        },
        {
          "code": "psychic",
          "label": "psychic"
        },
        {
          "code": "psychoanalyst",
          "label": "psychoanalyst"
        },
        {
          "code": "psychologist",
          "label": "psychologist"
        },
        {
          "code": "psychomotor_therapist",
          "label": "psychomotor therapist"
        },
        {
          "code": "psychoneurological_specialized_clinic",
          "label": "psychoneurological specialized clinic"
        },
        {
          "code": "psychopedagogy_clinic",
          "label": "psychopedagogy clinic"
        },
        {
          "code": "psychosomatic_medical_practitioner",
          "label": "psychosomatic medical practitioner"
        },
        {
          "code": "psychotherapist",
          "label": "psychotherapist"
        },
        {
          "code": "pub",
          "label": "pub"
        },
        {
          "code": "public_amenity_house",
          "label": "public amenity house"
        },
        {
          "code": "public_bath",
          "label": "public bath"
        },
        {
          "code": "public_bathroom",
          "label": "public bathroom"
        },
        {
          "code": "public_defenders_office",
          "label": "public defender's office"
        },
        {
          "code": "public_female_bathroom",
          "label": "public female bathroom"
        },
        {
          "code": "public_golf_course",
          "label": "public golf course"
        },
        {
          "code": "public_health_department",
          "label": "public health department"
        },
        {
          "code": "public_housing",
          "label": "public housing"
        },
        {
          "code": "public_library",
          "label": "public library"
        },
        {
          "code": "public_male_bathroom",
          "label": "public male bathroom"
        },
        {
          "code": "public_medical_center",
          "label": "public medical center"
        },
        {
          "code": "public_parking_space",
          "label": "public parking space"
        },
        {
          "code": "public_prosecutors_office",
          "label": "public prosecutors office"
        },
        {
          "code": "public_relations_firm",
          "label": "public relations firm"
        },
        {
          "code": "public_safety_office",
          "label": "public safety office"
        },
        {
          "code": "public_sauna",
          "label": "public sauna"
        },
        {
          "code": "public_school",
          "label": "public school"
        },
        {
          "code": "public_sector_bank",
          "label": "public sector bank"
        },
        {
          "code": "public_swimming_pool",
          "label": "public swimming pool"
        },
        {
          "code": "public_university",
          "label": "public university"
        },
        {
          "code": "public_webcam",
          "label": "public webcam"
        },
        {
          "code": "public_wheelchair_accessible_bathroom",
          "label": "public wheelchair-accessible bathroom"
        },
        {
          "code": "public_works_department",
          "label": "public works department"
        },
        {
          "code": "publisher",
          "label": "publisher"
        },
        {
          "code": "pueblan_restaurant",
          "label": "pueblan restaurant"
        },
        {
          "code": "puerto_rican_restaurant",
          "label": "puerto rican restaurant"
        },
        {
          "code": "pulmonologist",
          "label": "pulmonologist"
        },
        {
          "code": "pump_supplier",
          "label": "pump supplier"
        },
        {
          "code": "pumping_equipment_and_service",
          "label": "pumping equipment and service"
        },
        {
          "code": "pumpkin_patch",
          "label": "pumpkin patch"
        },
        {
          "code": "punjabi_restaurant",
          "label": "punjabi restaurant"
        },
        {
          "code": "puppet_theater",
          "label": "puppet theater"
        },
        {
          "code": "pvc_industry",
          "label": "pvc industry"
        },
        {
          "code": "pvc_windows_supplier",
          "label": "pvc windows supplier"
        },
        {
          "code": "qing_fang_market_place",
          "label": "qing fang market place"
        },
        {
          "code": "quaker_church",
          "label": "quaker church"
        },
        {
          "code": "quantity_surveyor",
          "label": "quantity surveyor"
        },
        {
          "code": "quarry",
          "label": "quarry"
        },
        {
          "code": "quebecois_restaurant",
          "label": "qu�b�cois restaurant"
        },
        {
          "code": "quilt_shop",
          "label": "quilt shop"
        },
        {
          "code": "race_car_dealer",
          "label": "race car dealer"
        },
        {
          "code": "race_course",
          "label": "racecourse"
        },
        {
          "code": "racing_car_parts_store",
          "label": "racing car parts store"
        },
        {
          "code": "raclette_restaurant",
          "label": "raclette restaurant"
        },
        {
          "code": "racquetball_club",
          "label": "racquetball club"
        },
        {
          "code": "radiator_repair_service",
          "label": "radiator repair service"
        },
        {
          "code": "radiator_shop",
          "label": "radiator shop"
        },
        {
          "code": "radio_broadcaster",
          "label": "radio broadcaster"
        },
        {
          "code": "radiologist",
          "label": "radiologist"
        },
        {
          "code": "raft_trip_outfitter",
          "label": "raft trip outfitter"
        },
        {
          "code": "rafting",
          "label": "rafting"
        },
        {
          "code": "rail_museum",
          "label": "rail museum"
        },
        {
          "code": "railing_contractor",
          "label": "railing contractor"
        },
        {
          "code": "railroad_company",
          "label": "railroad company"
        },
        {
          "code": "railroad_contractor",
          "label": "railroad contractor"
        },
        {
          "code": "railroad_equipment_supplier",
          "label": "railroad equipment supplier"
        },
        {
          "code": "railroad_ties_supplier",
          "label": "railroad ties supplier"
        },
        {
          "code": "railway_services",
          "label": "railway services"
        },
        {
          "code": "rainwater_tank_supplier",
          "label": "rainwater tank supplier"
        },
        {
          "code": "ramen_restaurant",
          "label": "ramen restaurant"
        },
        {
          "code": "ranch",
          "label": "ranch"
        },
        {
          "code": "rare_book_store",
          "label": "rare book store"
        },
        {
          "code": "raw_food_restaurant",
          "label": "raw food restaurant"
        },
        {
          "code": "ready_mix_concrete_supplier",
          "label": "ready mix concrete supplier"
        },
        {
          "code": "real_estate_agency",
          "label": "real estate agency"
        },
        {
          "code": "real_estate_agents",
          "label": "real estate agents"
        },
        {
          "code": "real_estate_appraiser",
          "label": "real estate appraiser"
        },
        {
          "code": "real_estate_attorney",
          "label": "real estate attorney"
        },
        {
          "code": "real_estate_auctioneer",
          "label": "real estate auctioneer"
        },
        {
          "code": "real_estate_consultant",
          "label": "real estate consultant"
        },
        {
          "code": "real_estate_developer",
          "label": "real estate developer"
        },
        {
          "code": "real_estate_fair",
          "label": "real estate fair"
        },
        {
          "code": "real_estate_rental_agency",
          "label": "real estate rental agency"
        },
        {
          "code": "real_estate_school",
          "label": "real estate school"
        },
        {
          "code": "real_estate_surveyor",
          "label": "real estate surveyor"
        },
        {
          "code": "reclamation_centre",
          "label": "reclamation centre"
        },
        {
          "code": "record_company",
          "label": "record company"
        },
        {
          "code": "record_storage_facility",
          "label": "records storage facility"
        },
        {
          "code": "record_store",
          "label": "record store"
        },
        {
          "code": "recording_studio",
          "label": "recording studio"
        },
        {
          "code": "recreation_center",
          "label": "recreation center"
        },
        {
          "code": "recruiter",
          "label": "recruiter"
        },
        {
          "code": "rectory",
          "label": "rectory"
        },
        {
          "code": "recycling_center",
          "label": "recycling center"
        },
        {
          "code": "reenactment_site",
          "label": "reenactment site"
        },
        {
          "code": "reflexologist",
          "label": "reflexologist"
        },
        {
          "code": "reform_synagogue",
          "label": "reform synagogue"
        },
        {
          "code": "reformed_church",
          "label": "reformed church"
        },
        {
          "code": "refrigerated_transport_service",
          "label": "refrigerated transport service"
        },
        {
          "code": "refrigerator_repair_service",
          "label": "refrigerator repair service"
        },
        {
          "code": "refrigerator_store",
          "label": "refrigerator store"
        },
        {
          "code": "refugee_camp",
          "label": "refugee camp"
        },
        {
          "code": "regional_airport",
          "label": "regional airport"
        },
        {
          "code": "regional_council",
          "label": "regional council"
        },
        {
          "code": "regional_government_office",
          "label": "regional government office"
        },
        {
          "code": "registered_general_nurse",
          "label": "registered general nurse"
        },
        {
          "code": "registration_chamber",
          "label": "registration chamber"
        },
        {
          "code": "registration_office",
          "label": "registration office"
        },
        {
          "code": "registry_office",
          "label": "registry office"
        },
        {
          "code": "rehabilitation_center",
          "label": "rehabilitation center"
        },
        {
          "code": "reiki_therapist",
          "label": "reiki therapist"
        },
        {
          "code": "religious_book_store",
          "label": "religious book store"
        },
        {
          "code": "religious_destination",
          "label": "religious destination"
        },
        {
          "code": "religious_goods_store",
          "label": "religious goods store"
        },
        {
          "code": "religious_institution",
          "label": "religious institution"
        },
        {
          "code": "religious_organization",
          "label": "religious organization"
        },
        {
          "code": "religious_school",
          "label": "religious school"
        },
        {
          "code": "religious_seminary",
          "label": "religious seminary"
        },
        {
          "code": "remodeler",
          "label": "remodeler"
        },
        {
          "code": "renault_dealer",
          "label": "renault dealer"
        },
        {
          "code": "renters_insurance_agency",
          "label": "renter's insurance agency"
        },
        {
          "code": "repair_service",
          "label": "repair service"
        },
        {
          "code": "reproductive_health_clinic",
          "label": "reproductive health clinic"
        },
        {
          "code": "reptile_store",
          "label": "reptile store"
        },
        {
          "code": "research_and_product_development",
          "label": "research and product development"
        },
        {
          "code": "research_engineer",
          "label": "research engineer"
        },
        {
          "code": "research_foundation",
          "label": "research foundation"
        },
        {
          "code": "research_institute",
          "label": "research institute"
        },
        {
          "code": "resident_registration_office",
          "label": "resident registration office"
        },
        {
          "code": "residential_college",
          "label": "residential college"
        },
        {
          "code": "residents_association",
          "label": "residents association"
        },
        {
          "code": "resort_hotel",
          "label": "resort"
        },
        {
          "code": "rest_stop",
          "label": "rest stop"
        },
        {
          "code": "restaurant",
          "label": "restaurant"
        },
        {
          "code": "restaurant_brasserie",
          "label": "brasserie"
        },
        {
          "code": "restaurant_supply_store",
          "label": "restaurant supply store"
        },
        {
          "code": "resume_service",
          "label": "resume service"
        },
        {
          "code": "retail_space_rental_agency",
          "label": "retail space rental agency"
        },
        {
          "code": "retaining_wall_supplier",
          "label": "retaining wall supplier"
        },
        {
          "code": "retirement_community",
          "label": "retirement community"
        },
        {
          "code": "retirement_home",
          "label": "retirement home"
        },
        {
          "code": "retreat_center",
          "label": "retreat center"
        },
        {
          "code": "rheumatologist",
          "label": "rheumatologist"
        },
        {
          "code": "rice_cake_shop",
          "label": "rice cake shop"
        },
        {
          "code": "rice_cracker_shop",
          "label": "rice cracker shop"
        },
        {
          "code": "rice_mill",
          "label": "rice mill"
        },
        {
          "code": "rice_restaurant",
          "label": "rice restaurant"
        },
        {
          "code": "rice_shop",
          "label": "rice shop"
        },
        {
          "code": "rice_wholesaler",
          "label": "rice wholesaler"
        },
        {
          "code": "river_port",
          "label": "river port"
        },
        {
          "code": "road_construction_company",
          "label": "road construction company"
        },
        {
          "code": "road_construction_machine_repair_service",
          "label": "road construction machine repair service"
        },
        {
          "code": "road_cycling",
          "label": "road cycling"
        },
        {
          "code": "road_safety_town",
          "label": "road safety town"
        },
        {
          "code": "roads_ports_and_canals_engineers_association",
          "label": "roads ports and canals engineers association"
        },
        {
          "code": "rock_climbing",
          "label": "rock climbing"
        },
        {
          "code": "rock_climbing_centre",
          "label": "rock climbing gym"
        },
        {
          "code": "rock_climbing_instructor",
          "label": "rock climbing instructor"
        },
        {
          "code": "rock_music_club",
          "label": "rock music club"
        },
        {
          "code": "rock_shop",
          "label": "rock shop"
        },
        {
          "code": "rodeo",
          "label": "rodeo"
        },
        {
          "code": "rolled_metal_products_supplier",
          "label": "rolled metal products supplier"
        },
        {
          "code": "roller_coaster",
          "label": "roller coaster"
        },
        {
          "code": "roller_skating_club",
          "label": "roller skating club"
        },
        {
          "code": "roller_skating_rink",
          "label": "roller skating rink"
        },
        {
          "code": "rolls_royce_dealer",
          "label": "rolls royce dealer"
        },
        {
          "code": "roman_restaurant",
          "label": "roman restaurant"
        },
        {
          "code": "romanian_restaurant",
          "label": "romanian restaurant"
        },
        {
          "code": "roofing_contractor",
          "label": "roofing contractor"
        },
        {
          "code": "roofing_supply_store",
          "label": "roofing supply store"
        },
        {
          "code": "roommate_referral_service",
          "label": "roommate referral service"
        },
        {
          "code": "rowing_area",
          "label": "rowing area"
        },
        {
          "code": "rowing_club",
          "label": "rowing club"
        },
        {
          "code": "rsl_club",
          "label": "rsl club"
        },
        {
          "code": "rubber_products_supplier",
          "label": "rubber products supplier"
        },
        {
          "code": "rubber_stamp_store",
          "label": "rubber stamp store"
        },
        {
          "code": "rug_store",
          "label": "rug store"
        },
        {
          "code": "rugby",
          "label": "rugby"
        },
        {
          "code": "rugby_club",
          "label": "rugby club"
        },
        {
          "code": "rugby_field",
          "label": "rugby field"
        },
        {
          "code": "rugby_league_club",
          "label": "rugby league club"
        },
        {
          "code": "rugby_store",
          "label": "rugby store"
        },
        {
          "code": "running_store",
          "label": "running store"
        },
        {
          "code": "russian_grocery_store",
          "label": "russian grocery store"
        },
        {
          "code": "russian_orthodox_church",
          "label": "russian orthodox church"
        },
        {
          "code": "russian_restaurant",
          "label": "russian restaurant"
        },
        {
          "code": "rustic_furniture_store",
          "label": "rustic furniture store"
        },
        {
          "code": "rv_dealer",
          "label": "rv dealer"
        },
        {
          "code": "rv_park",
          "label": "rv park"
        },
        {
          "code": "rv_rental_agency",
          "label": "recreational vehicle rental agency"
        },
        {
          "code": "rv_repair_shop",
          "label": "rv repair shop"
        },
        {
          "code": "rv_storage_facility",
          "label": "rv storage facility"
        },
        {
          "code": "rv_supply_store",
          "label": "rv supply store"
        },
        {
          "code": "saab_dealer",
          "label": "saab dealer"
        },
        {
          "code": "sacem",
          "label": "sacem"
        },
        {
          "code": "saddlery",
          "label": "saddlery"
        },
        {
          "code": "safe_and_vault_shop",
          "label": "safe & vault shop"
        },
        {
          "code": "safety_equipment_supplier",
          "label": "safety equipment supplier"
        },
        {
          "code": "sailing_club",
          "label": "sailing club"
        },
        {
          "code": "sailing_event_area",
          "label": "sailing event area"
        },
        {
          "code": "sailing_school",
          "label": "sailing school"
        },
        {
          "code": "sailmaker",
          "label": "sailmaker"
        },
        {
          "code": "sake_brewery",
          "label": "sake brewery"
        },
        {
          "code": "salad_shop",
          "label": "salad shop"
        },
        {
          "code": "salsa_bar",
          "label": "salsa bar"
        },
        {
          "code": "salsa_classes",
          "label": "salsa classes"
        },
        {
          "code": "salvadoran_restaurant",
          "label": "salvadoran restaurant"
        },
        {
          "code": "salvage_dealer",
          "label": "salvage dealer"
        },
        {
          "code": "salvage_yard",
          "label": "salvage yard"
        },
        {
          "code": "samba_school",
          "label": "samba school"
        },
        {
          "code": "sambo_school",
          "label": "sambo school"
        },
        {
          "code": "sambodrome",
          "label": "sambodrome"
        },
        {
          "code": "sand_and_gravel_supplier",
          "label": "sand & gravel supplier"
        },
        {
          "code": "sand_plant",
          "label": "sand plant"
        },
        {
          "code": "sandblasting_service",
          "label": "sandblasting service"
        },
        {
          "code": "sandwich_shop",
          "label": "sandwich shop"
        },
        {
          "code": "sanitary_inspection",
          "label": "sanitary inspection"
        },
        {
          "code": "sanitation_service",
          "label": "sanitation service"
        },
        {
          "code": "sardinian_restaurant",
          "label": "sardinian restaurant"
        },
        {
          "code": "satay_restaurant",
          "label": "satay restaurant"
        },
        {
          "code": "satellite_communication_service",
          "label": "satellite communication service"
        },
        {
          "code": "saturn_dealer",
          "label": "saturn dealer"
        },
        {
          "code": "sauna",
          "label": "sauna"
        },
        {
          "code": "sauna_club",
          "label": "sauna club"
        },
        {
          "code": "sauna_store",
          "label": "sauna store"
        },
        {
          "code": "savings_bank",
          "label": "savings bank"
        },
        {
          "code": "saw_mill",
          "label": "saw mill"
        },
        {
          "code": "saw_sharpening_service",
          "label": "saw sharpening service"
        },
        {
          "code": "scaffolder",
          "label": "scaffolder"
        },
        {
          "code": "scaffolding_rental_service",
          "label": "scaffolding rental service"
        },
        {
          "code": "scale_model_club",
          "label": "scale model club"
        },
        {
          "code": "scale_model_shop",
          "label": "model shop"
        },
        {
          "code": "scale_repair_service",
          "label": "scale repair service"
        },
        {
          "code": "scale_supplier",
          "label": "scale supplier"
        },
        {
          "code": "scandinavian_restaurant",
          "label": "scandinavian restaurant"
        },
        {
          "code": "scenic_spot",
          "label": "scenic spot"
        },
        {
          "code": "school",
          "label": "school"
        },
        {
          "code": "school_administrator",
          "label": "school administrator"
        },
        {
          "code": "school_bus_service",
          "label": "school bus service"
        },
        {
          "code": "school_center",
          "label": "school center"
        },
        {
          "code": "school_district_office",
          "label": "school district office"
        },
        {
          "code": "school_for_the_deaf",
          "label": "school for the deaf"
        },
        {
          "code": "school_house",
          "label": "school house"
        },
        {
          "code": "school_lunch_center",
          "label": "school lunch center"
        },
        {
          "code": "school_supply_store",
          "label": "school supply store"
        },
        {
          "code": "science_academy",
          "label": "science academy"
        },
        {
          "code": "science_museum",
          "label": "science museum"
        },
        {
          "code": "scientific_equipment_supplier",
          "label": "scientific equipment supplier"
        },
        {
          "code": "scooter_rental_service",
          "label": "scooter rental service"
        },
        {
          "code": "scooter_repair_shop",
          "label": "scooter repair shop"
        },
        {
          "code": "scout_hall",
          "label": "scout hall"
        },
        {
          "code": "scout_home",
          "label": "scout home"
        },
        {
          "code": "scouting",
          "label": "scouting"
        },
        {
          "code": "scrap_metal_dealer",
          "label": "scrap metal dealer"
        },
        {
          "code": "scrapbooking_store",
          "label": "scrapbooking store"
        },
        {
          "code": "screen_printer",
          "label": "screen printer"
        },
        {
          "code": "screen_printing_shop",
          "label": "screen printing shop"
        },
        {
          "code": "screen_printing_supply_store",
          "label": "screen printing supply store"
        },
        {
          "code": "screen_repair_service",
          "label": "screen repair service"
        },
        {
          "code": "screen_store",
          "label": "screen store"
        },
        {
          "code": "screw_supplier",
          "label": "screw supplier"
        },
        {
          "code": "scuba_instructor",
          "label": "scuba instructor"
        },
        {
          "code": "scuba_tour_agency",
          "label": "scuba tour agency"
        },
        {
          "code": "sculptor",
          "label": "sculptor"
        },
        {
          "code": "sculpture",
          "label": "sculpture"
        },
        {
          "code": "sculpture_museum",
          "label": "sculpture museum"
        },
        {
          "code": "seafood_donburi",
          "label": "seafood donburi restaurant"
        },
        {
          "code": "seafood_farm",
          "label": "seafood farm"
        },
        {
          "code": "seafood_market",
          "label": "seafood market"
        },
        {
          "code": "seafood_restaurant",
          "label": "seafood restaurant"
        },
        {
          "code": "seafood_wholesaler",
          "label": "seafood wholesaler"
        },
        {
          "code": "seal_shop",
          "label": "seal shop"
        },
        {
          "code": "seaplane_base",
          "label": "seaplane base"
        },
        {
          "code": "seasonal_goods_store",
          "label": "seasonal goods store"
        },
        {
          "code": "seat_dealer",
          "label": "seat dealer"
        },
        {
          "code": "second_hand_shop",
          "label": "second hand store"
        },
        {
          "code": "secondary_school_three",
          "label": "secondary school three"
        },
        {
          "code": "security_guard_service",
          "label": "security guard service"
        },
        {
          "code": "security_service",
          "label": "security service"
        },
        {
          "code": "security_system_installer",
          "label": "security system installer"
        },
        {
          "code": "security_system_supplier",
          "label": "security system supplier"
        },
        {
          "code": "seed_supplier",
          "label": "seed supplier"
        },
        {
          "code": "seitai",
          "label": "seitai"
        },
        {
          "code": "self_catering_accommodation",
          "label": "self-catering accommodation"
        },
        {
          "code": "self_defense_school",
          "label": "self defense school"
        },
        {
          "code": "self_service_car_wash",
          "label": "self service car wash"
        },
        {
          "code": "self_service_health_station",
          "label": "self service health station"
        },
        {
          "code": "self_service_restaurant",
          "label": "self service restaurant"
        },
        {
          "code": "self_storage_facility",
          "label": "self-storage facility"
        },
        {
          "code": "semi_conductor_supplier",
          "label": "semi conductor supplier"
        },
        {
          "code": "seminary",
          "label": "seminary"
        },
        {
          "code": "senior_citizen_center",
          "label": "senior citizen center"
        },
        {
          "code": "senior_citizens_care_service",
          "label": "aged care"
        },
        {
          "code": "senior_high_school",
          "label": "senior high school"
        },
        {
          "code": "septic_system_service",
          "label": "septic system service"
        },
        {
          "code": "serbian_restaurant",
          "label": "serbian restaurant"
        },
        {
          "code": "serviced_accommodation",
          "label": "serviced accommodation"
        },
        {
          "code": "seventh_day_adventist_church",
          "label": "seventh-day adventist church"
        },
        {
          "code": "sewage_disposal_service",
          "label": "sewage disposal service"
        },
        {
          "code": "sewage_treatment_plant",
          "label": "sewage treatment plant"
        },
        {
          "code": "sewing_company",
          "label": "sewing company"
        },
        {
          "code": "sewing_machine_repair_service",
          "label": "sewing machine repair service"
        },
        {
          "code": "sewing_machine_store",
          "label": "sewing machine store"
        },
        {
          "code": "sewing_shop",
          "label": "sewing shop"
        },
        {
          "code": "sexologist",
          "label": "sexologist"
        },
        {
          "code": "seychelles_restaurant",
          "label": "seychelles restaurant"
        },
        {
          "code": "sfiha_restaurant",
          "label": "sfiha restaurant"
        },
        {
          "code": "shabu_shabu_and_sukiyaki_restaurant",
          "label": "sukiyaki and shabu shabu restaurant"
        },
        {
          "code": "shabu_shabu_restaurant",
          "label": "shabu-shabu restaurant"
        },
        {
          "code": "shan_dong_restaurant",
          "label": "shandong restaurant"
        },
        {
          "code": "shanghainese_restaurant",
          "label": "shanghainese restaurant"
        },
        {
          "code": "sharpening_service",
          "label": "sharpening service"
        },
        {
          "code": "shed_builder",
          "label": "shed builder"
        },
        {
          "code": "sheep_shearer",
          "label": "sheep shearer"
        },
        {
          "code": "sheepskin_and_wool_products_supplier",
          "label": "sheepskin and wool products supplier"
        },
        {
          "code": "sheepskin_coat_store",
          "label": "sheepskin coat store"
        },
        {
          "code": "sheet_metal_contractor",
          "label": "sheet metal contractor"
        },
        {
          "code": "sheet_music_store",
          "label": "sheet music store"
        },
        {
          "code": "shelter",
          "label": "shelter"
        },
        {
          "code": "sheltered_housing",
          "label": "sheltered housing"
        },
        {
          "code": "shelving_store",
          "label": "shelving store"
        },
        {
          "code": "sheriffs_department",
          "label": "sheriff's department"
        },
        {
          "code": "shinkin_bank",
          "label": "shinkin bank"
        },
        {
          "code": "shinto_shrine",
          "label": "shinto shrine"
        },
        {
          "code": "ship_building",
          "label": "ship building"
        },
        {
          "code": "shipbuilding_and_repair_company",
          "label": "shipbuilding and repair company"
        },
        {
          "code": "shipping_and_mailing_service",
          "label": "shipping and mailing service"
        },
        {
          "code": "shipping_company",
          "label": "shipping company"
        },
        {
          "code": "shipping_equipment_industry",
          "label": "shipping equipment industry"
        },
        {
          "code": "shipping_service",
          "label": "shipping service"
        },
        {
          "code": "shipyard",
          "label": "shipyard"
        },
        {
          "code": "shochu_brewery",
          "label": "shochu brewery"
        },
        {
          "code": "shoe_factory",
          "label": "shoe factory"
        },
        {
          "code": "shoe_repair_shop",
          "label": "shoe repair shop"
        },
        {
          "code": "shoe_shining_service",
          "label": "shoe shining service"
        },
        {
          "code": "shoe_store",
          "label": "shoe store"
        },
        {
          "code": "shoe_wholesaler",
          "label": "footwear wholesaler"
        },
        {
          "code": "shogi_lesson",
          "label": "shogi lesson"
        },
        {
          "code": "shooting_event_area",
          "label": "shooting event area"
        },
        {
          "code": "shooting_range",
          "label": "shooting range"
        },
        {
          "code": "shop_supermarket_furniture_store",
          "label": "shop supermarket furniture store"
        },
        {
          "code": "shopfitter",
          "label": "shopfitter"
        },
        {
          "code": "shopping_center",
          "label": "shopping mall"
        },
        {
          "code": "short_term_apartment_rental_agency",
          "label": "short term apartment rental agency"
        },
        {
          "code": "shower_door_shop",
          "label": "shower door shop"
        },
        {
          "code": "shredding_service",
          "label": "shredding service"
        },
        {
          "code": "shrimp_farm",
          "label": "shrimp farm"
        },
        {
          "code": "shrine",
          "label": "shrine"
        },
        {
          "code": "sichuan_restaurant",
          "label": "sichuan restaurant"
        },
        {
          "code": "sicilian_restaurant",
          "label": "sicilian restaurant"
        },
        {
          "code": "siding_contractor",
          "label": "siding contractor"
        },
        {
          "code": "sightseeing_tour_agency",
          "label": "sightseeing tour agency"
        },
        {
          "code": "sign_shop",
          "label": "sign shop"
        },
        {
          "code": "sikh_temple",
          "label": "gurudwara"
        },
        {
          "code": "silk_plant_shop",
          "label": "silk plant shop"
        },
        {
          "code": "silk_store",
          "label": "silk store"
        },
        {
          "code": "silversmith",
          "label": "silversmith"
        },
        {
          "code": "singaporean_restaurant",
          "label": "singaporean restaurant"
        },
        {
          "code": "singing_telegram_service",
          "label": "singing telegram service"
        },
        {
          "code": "single_sex_secondary_school",
          "label": "single sex secondary school"
        },
        {
          "code": "singles_organization",
          "label": "singles organization"
        },
        {
          "code": "sixth_form_college",
          "label": "sixth form college"
        },
        {
          "code": "skate_sharpening_service",
          "label": "skate sharpening service"
        },
        {
          "code": "skate_shop",
          "label": "skate shop"
        },
        {
          "code": "skateboard_park",
          "label": "skateboard park"
        },
        {
          "code": "skateboard_shop",
          "label": "skateboard shop"
        },
        {
          "code": "skating_instructor",
          "label": "skating instructor"
        },
        {
          "code": "skeet_shooting_range",
          "label": "skeet shooting range"
        },
        {
          "code": "skewer_deep_frying",
          "label": "kushiage and kushikatsu restaurant"
        },
        {
          "code": "ski_club",
          "label": "ski club"
        },
        {
          "code": "ski_rental_service",
          "label": "ski rental service"
        },
        {
          "code": "ski_repair_service",
          "label": "ski repair service"
        },
        {
          "code": "ski_resort",
          "label": "ski resort"
        },
        {
          "code": "ski_school",
          "label": "ski school"
        },
        {
          "code": "ski_store",
          "label": "ski shop"
        },
        {
          "code": "skin_care_clinic",
          "label": "skin care clinic"
        },
        {
          "code": "skin_care_products_vending_machine",
          "label": "skin care products vending machine"
        },
        {
          "code": "skittle_club",
          "label": "skittle club"
        },
        {
          "code": "skoda_dealer",
          "label": "skoda dealer"
        },
        {
          "code": "skydiving_center",
          "label": "skydiving center"
        },
        {
          "code": "skylight_contractor",
          "label": "skylight contractor"
        },
        {
          "code": "slaughterhouse",
          "label": "slaughterhouse"
        },
        {
          "code": "sleep_clinic",
          "label": "sleep clinic"
        },
        {
          "code": "small_appliance_repair_service",
          "label": "small appliance repair service"
        },
        {
          "code": "small_claims_assistance_service",
          "label": "small claims assistance service"
        },
        {
          "code": "small_engine_repair_service",
          "label": "small engine repair service"
        },
        {
          "code": "small_plates_restaurant",
          "label": "small plates restaurant"
        },
        {
          "code": "smart_car_dealer",
          "label": "smart car dealer"
        },
        {
          "code": "smart_dealer",
          "label": "smart dealer"
        },
        {
          "code": "smart_shop",
          "label": "smart shop"
        },
        {
          "code": "smog_inspection_station",
          "label": "smog inspection station"
        },
        {
          "code": "snack_bar",
          "label": "snack bar"
        },
        {
          "code": "snow_removal_service",
          "label": "snow removal service"
        },
        {
          "code": "snowboard_rental_service",
          "label": "snowboard rental service"
        },
        {
          "code": "snowboard_shop",
          "label": "snowboard shop"
        },
        {
          "code": "snowmobile_dealer",
          "label": "snowmobile dealer"
        },
        {
          "code": "snowmobile_rental_service",
          "label": "snowmobile rental service"
        },
        {
          "code": "soapland",
          "label": "soapland"
        },
        {
          "code": "soba_noodle_shop",
          "label": "soba noodle shop"
        },
        {
          "code": "soccer_club",
          "label": "soccer club"
        },
        {
          "code": "soccer_field",
          "label": "soccer field"
        },
        {
          "code": "soccer_practice",
          "label": "soccer practice"
        },
        {
          "code": "soccer_store",
          "label": "soccer store"
        },
        {
          "code": "social_club",
          "label": "social club"
        },
        {
          "code": "social_security_attorney",
          "label": "social security attorney"
        },
        {
          "code": "social_security_financial_department",
          "label": "social security financial department"
        },
        {
          "code": "social_security_office",
          "label": "social security office"
        },
        {
          "code": "social_services_organization",
          "label": "social services organization"
        },
        {
          "code": "social_welfare_center",
          "label": "social welfare center"
        },
        {
          "code": "social_worker",
          "label": "social worker"
        },
        {
          "code": "societe_de_flocage",
          "label": "societe de flocage"
        },
        {
          "code": "sod_supplier",
          "label": "sod supplier"
        },
        {
          "code": "sofa_store",
          "label": "sofa store"
        },
        {
          "code": "soft_drinks_shop",
          "label": "soft drinks shop"
        },
        {
          "code": "soft_shelled_turtle_dish_restaurant",
          "label": "suppon restaurant"
        },
        {
          "code": "softball_club",
          "label": "softball club"
        },
        {
          "code": "softball_field",
          "label": "softball field"
        },
        {
          "code": "software_company",
          "label": "software company"
        },
        {
          "code": "software_training_institute",
          "label": "software training institute"
        },
        {
          "code": "soil_testing_service",
          "label": "soil testing service"
        },
        {
          "code": "sokol_house",
          "label": "sokol house"
        },
        {
          "code": "solar_energy_company",
          "label": "solar energy company"
        },
        {
          "code": "solar_energy_contractor",
          "label": "solar energy contractor"
        },
        {
          "code": "solar_energy_equipment_supplier",
          "label": "solar energy equipment supplier"
        },
        {
          "code": "solar_hot_water_system_supplier",
          "label": "solar hot water system supplier"
        },
        {
          "code": "solar_photovoltaic_power_plant",
          "label": "solar photovoltaic power plant"
        },
        {
          "code": "solid_fuel_company",
          "label": "solid fuel company"
        },
        {
          "code": "solid_waste_engineer",
          "label": "solid waste engineer"
        },
        {
          "code": "soondae_restaurant",
          "label": "soondae restaurant"
        },
        {
          "code": "soto_ayam_restaurant",
          "label": "soto ayam restaurant"
        },
        {
          "code": "soul_food_restaurant",
          "label": "soul food restaurant"
        },
        {
          "code": "soup_kitchen",
          "label": "soup kitchen"
        },
        {
          "code": "soup_restaurant",
          "label": "soup restaurant"
        },
        {
          "code": "soup_shop",
          "label": "soup shop"
        },
        {
          "code": "south_african_restaurant",
          "label": "south african restaurant"
        },
        {
          "code": "south_american_restaurant",
          "label": "south american restaurant"
        },
        {
          "code": "south_asia_restaurant",
          "label": "south asian restaurant"
        },
        {
          "code": "south_east_asian_restaurant",
          "label": "southeast asian restaurant"
        },
        {
          "code": "south_sulawesi_restaurant",
          "label": "south sulawesi restaurant"
        },
        {
          "code": "southern_italian_restaurant",
          "label": "southern italian restaurant"
        },
        {
          "code": "southern_us_restaurant",
          "label": "southern restaurant (us)"
        },
        {
          "code": "southwest_french_restaurant",
          "label": "southwest france restaurant"
        },
        {
          "code": "southwestern_us_restaurant",
          "label": "southwestern restaurant (us)"
        },
        {
          "code": "souvenir_manufacturer",
          "label": "souvenir manufacturer"
        },
        {
          "code": "souvenir_store",
          "label": "souvenir store"
        },
        {
          "code": "soy_sauce_maker",
          "label": "soy sauce maker"
        },
        {
          "code": "spa",
          "label": "spa"
        },
        {
          "code": "spa_and_health_club",
          "label": "spa and health club"
        },
        {
          "code": "spa_garden",
          "label": "spa garden"
        },
        {
          "code": "spa_town",
          "label": "spa town"
        },
        {
          "code": "spanish_restaurant",
          "label": "spanish restaurant"
        },
        {
          "code": "special_education_school",
          "label": "special education school"
        },
        {
          "code": "specialized_clinic",
          "label": "specialized clinic"
        },
        {
          "code": "specialized_hospital",
          "label": "specialized hospital"
        },
        {
          "code": "speech_pathologist",
          "label": "speech pathologist"
        },
        {
          "code": "sperm_bank",
          "label": "sperm bank"
        },
        {
          "code": "spice_store",
          "label": "spice store"
        },
        {
          "code": "spices_exporter",
          "label": "spices exporter"
        },
        {
          "code": "spices_wholesalers",
          "label": "spices wholesalers"
        },
        {
          "code": "spiritist_center",
          "label": "spiritist center"
        },
        {
          "code": "sport_tour_agency",
          "label": "sport tour agency"
        },
        {
          "code": "sporting_goods_store",
          "label": "sporting goods store"
        },
        {
          "code": "sports_accessories_wholesaler",
          "label": "sports accessories wholesaler"
        },
        {
          "code": "sports_bar",
          "label": "sports bar"
        },
        {
          "code": "sports_card_store",
          "label": "sports card store"
        },
        {
          "code": "sports_club",
          "label": "sports club"
        },
        {
          "code": "sports_complex",
          "label": "sports complex"
        },
        {
          "code": "sports_equipment_rental_service",
          "label": "sports equipment rental service"
        },
        {
          "code": "sports_massage_therapist",
          "label": "sports massage therapist"
        },
        {
          "code": "sports_medicine_clinic",
          "label": "sports medicine clinic"
        },
        {
          "code": "sports_medicine_physician",
          "label": "sports medicine physician"
        },
        {
          "code": "sports_memorabilia_store",
          "label": "sports memorabilia store"
        },
        {
          "code": "sports_nutrition_store",
          "label": "sports nutrition store"
        },
        {
          "code": "sports_school",
          "label": "sports school"
        },
        {
          "code": "sportswear_store",
          "label": "sportswear store"
        },
        {
          "code": "sportwear_manufacturer",
          "label": "sportwear manufacturer"
        },
        {
          "code": "spring_supplier",
          "label": "spring supplier"
        },
        {
          "code": "squash_club",
          "label": "squash club"
        },
        {
          "code": "squash_court",
          "label": "squash court"
        },
        {
          "code": "sri_lankan_restaurant",
          "label": "sri lankan restaurant"
        },
        {
          "code": "stable",
          "label": "stable"
        },
        {
          "code": "stadium",
          "label": "stadium"
        },
        {
          "code": "stage",
          "label": "stage"
        },
        {
          "code": "stage_lighting_equipment_supplier",
          "label": "stage lighting equipment supplier"
        },
        {
          "code": "stained_glass_studio",
          "label": "stained glass studio"
        },
        {
          "code": "stainless_steel_plant",
          "label": "stainless steel plant"
        },
        {
          "code": "stair_contractor",
          "label": "stair contractor"
        },
        {
          "code": "stall_installation_service",
          "label": "stall installation service"
        },
        {
          "code": "stamp_collectors_club",
          "label": "stamp collectors club"
        },
        {
          "code": "stamp_shop",
          "label": "stamp shop"
        },
        {
          "code": "stand_bar",
          "label": "stand bar"
        },
        {
          "code": "staple_food_package",
          "label": "staple food package"
        },
        {
          "code": "state_archive",
          "label": "state archive"
        },
        {
          "code": "state_department_agricultural_development",
          "label": "state department agricultural development"
        },
        {
          "code": "state_department_agriculture_food_supply",
          "label": "state department agriculture food supply"
        },
        {
          "code": "state_department_civil_defense",
          "label": "state department civil defense"
        },
        {
          "code": "state_department_communication",
          "label": "state department communication"
        },
        {
          "code": "state_department_finance",
          "label": "state department finance"
        },
        {
          "code": "state_department_for_social_development",
          "label": "state department for social development"
        },
        {
          "code": "state_department_housing_and_urban_development",
          "label": "state department housing and urban development"
        },
        {
          "code": "state_department_of_environment",
          "label": "state department of environment"
        },
        {
          "code": "state_department_of_tourism",
          "label": "state department of tourism"
        },
        {
          "code": "state_department_of_transportation",
          "label": "state department of transportation"
        },
        {
          "code": "state_department_science_technology",
          "label": "state department science technology"
        },
        {
          "code": "state_department_social_defense",
          "label": "state department social defense"
        },
        {
          "code": "state_dept_of_culture",
          "label": "state dept of culture"
        },
        {
          "code": "state_dept_of_sports",
          "label": "state dept of sports"
        },
        {
          "code": "state_employment_department",
          "label": "state employment department"
        },
        {
          "code": "state_government_office",
          "label": "state government office"
        },
        {
          "code": "state_liquor_store",
          "label": "state liquor store"
        },
        {
          "code": "state_office_of_education",
          "label": "state office of education"
        },
        {
          "code": "state_owned_farm",
          "label": "state owned farm"
        },
        {
          "code": "state_park",
          "label": "state park"
        },
        {
          "code": "state_police",
          "label": "state police"
        },
        {
          "code": "state_social_development",
          "label": "state social development"
        },
        {
          "code": "stationery_manufacturer",
          "label": "stationery manufacturer"
        },
        {
          "code": "stationery_store",
          "label": "stationery store"
        },
        {
          "code": "stationery_wholesaler",
          "label": "stationery wholesaler"
        },
        {
          "code": "statuary",
          "label": "statuary"
        },
        {
          "code": "std_clinic",
          "label": "std clinic"
        },
        {
          "code": "std_testing_service",
          "label": "std testing service"
        },
        {
          "code": "steak_house",
          "label": "steak house"
        },
        {
          "code": "steamboat_restaurant",
          "label": "steamboat restaurant"
        },
        {
          "code": "steamed_bun_shop",
          "label": "steamed bun shop"
        },
        {
          "code": "steel_construction_company",
          "label": "steel construction company"
        },
        {
          "code": "steel_distributor",
          "label": "steel distributor"
        },
        {
          "code": "steel_drum_supplier",
          "label": "steel drum supplier"
        },
        {
          "code": "steel_erector",
          "label": "steel erector"
        },
        {
          "code": "steel_fabricator",
          "label": "steel fabricator"
        },
        {
          "code": "steel_framework_contractor",
          "label": "steel framework contractor"
        },
        {
          "code": "steelwork_design_company",
          "label": "steelwork design company"
        },
        {
          "code": "steelwork_manufacturer",
          "label": "steelwork manufacturer"
        },
        {
          "code": "stereo_rental_store",
          "label": "stereo rental store"
        },
        {
          "code": "stereo_repair_service",
          "label": "stereo repair service"
        },
        {
          "code": "stereo_store",
          "label": "home audio store"
        },
        {
          "code": "sticker_manufacturer",
          "label": "sticker manufacturer"
        },
        {
          "code": "stitching_class",
          "label": "stitching class"
        },
        {
          "code": "stock_broker",
          "label": "stock broker"
        },
        {
          "code": "stock_exchange_building",
          "label": "stock exchange building"
        },
        {
          "code": "stone_carving",
          "label": "stone carving"
        },
        {
          "code": "stone_cutter",
          "label": "stone cutter"
        },
        {
          "code": "stone_supplier",
          "label": "stone supplier"
        },
        {
          "code": "storage_facility",
          "label": "storage facility"
        },
        {
          "code": "store",
          "label": "store"
        },
        {
          "code": "store_equipment_supplier",
          "label": "store equipment supplier"
        },
        {
          "code": "stove_builder",
          "label": "stove builder"
        },
        {
          "code": "stringed_intrument_maker",
          "label": "stringed instrument maker"
        },
        {
          "code": "structural_engineer",
          "label": "structural engineer"
        },
        {
          "code": "stucco_contractor",
          "label": "stucco contractor"
        },
        {
          "code": "student_career_counseling_office",
          "label": "student career counseling office"
        },
        {
          "code": "student_dormitory",
          "label": "student dormitory"
        },
        {
          "code": "student_housing_center",
          "label": "student housing center"
        },
        {
          "code": "student_union",
          "label": "student union"
        },
        {
          "code": "students_parents_association",
          "label": "students parents association"
        },
        {
          "code": "students_support_association",
          "label": "students support association"
        },
        {
          "code": "study_at_home_school",
          "label": "study at home school"
        },
        {
          "code": "studying_center",
          "label": "studying center"
        },
        {
          "code": "stylist",
          "label": "stylist"
        },
        {
          "code": "subaru_dealer",
          "label": "subaru dealer"
        },
        {
          "code": "suburban_train_line",
          "label": "suburban train line"
        },
        {
          "code": "sugar_factory",
          "label": "sugar factory"
        },
        {
          "code": "sugar_shack",
          "label": "sugar shack"
        },
        {
          "code": "sukiyaki_restaurant",
          "label": "sukiyaki restaurant"
        },
        {
          "code": "summer_camp",
          "label": "summer camp"
        },
        {
          "code": "summer_toboggan_run",
          "label": "summer toboggan run"
        },
        {
          "code": "sundae_restaurant",
          "label": "sundae restaurant"
        },
        {
          "code": "sundanese_restaurant",
          "label": "sundanese restaurant"
        },
        {
          "code": "sunglasses_store",
          "label": "sunglasses store"
        },
        {
          "code": "sunroom_contractor",
          "label": "sunroom contractor"
        },
        {
          "code": "super_public_bath",
          "label": "super public bath"
        },
        {
          "code": "superannuation_consultant",
          "label": "superannuation consultant"
        },
        {
          "code": "superfund_site",
          "label": "superfund site"
        },
        {
          "code": "supermarket",
          "label": "supermarket"
        },
        {
          "code": "surf_lifesaving_club",
          "label": "surf lifesaving club"
        },
        {
          "code": "surf_school",
          "label": "surf school"
        },
        {
          "code": "surf_shop",
          "label": "surf shop"
        },
        {
          "code": "surgeon",
          "label": "surgeon"
        },
        {
          "code": "surgical_center",
          "label": "surgical center"
        },
        {
          "code": "surgical_products_wholesaler",
          "label": "surgical products wholesaler"
        },
        {
          "code": "surgical_supply_store",
          "label": "surgical supply store"
        },
        {
          "code": "surinamese_restaurant",
          "label": "surinamese restaurant"
        },
        {
          "code": "surplus_store",
          "label": "surplus store"
        },
        {
          "code": "surveyor",
          "label": "surveyor"
        },
        {
          "code": "sushi_restaurant",
          "label": "sushi restaurant"
        },
        {
          "code": "sushi_takeaway",
          "label": "sushi takeaway"
        },
        {
          "code": "suzuki_dealer",
          "label": "suzuki dealer"
        },
        {
          "code": "suzuki_motorcycle_dealer",
          "label": "suzuki motorcycle dealer"
        },
        {
          "code": "swedish_restaurant",
          "label": "swedish restaurant"
        },
        {
          "code": "swim_club",
          "label": "swim club"
        },
        {
          "code": "swimming_basin",
          "label": "swimming basin"
        },
        {
          "code": "swimming_competition",
          "label": "swimming competition"
        },
        {
          "code": "swimming_facility",
          "label": "swimming facility"
        },
        {
          "code": "swimming_instructor",
          "label": "swimming instructor"
        },
        {
          "code": "swimming_lake",
          "label": "swimming lake"
        },
        {
          "code": "swimming_pool",
          "label": "swimming pool"
        },
        {
          "code": "swimming_pool_contractor",
          "label": "swimming pool contractor"
        },
        {
          "code": "swimming_pool_repair_service",
          "label": "swimming pool repair service"
        },
        {
          "code": "swimming_pool_supply_store",
          "label": "swimming pool supply store"
        },
        {
          "code": "swimming_school",
          "label": "swimming school"
        },
        {
          "code": "swimwear_store",
          "label": "swimwear store"
        },
        {
          "code": "swiss_restaurant",
          "label": "swiss restaurant"
        },
        {
          "code": "synagogue",
          "label": "synagogue"
        },
        {
          "code": "syrian_restaurant",
          "label": "syrian restaurant"
        },
        {
          "code": "t_shirt_company",
          "label": "t-shirt company"
        },
        {
          "code": "t_shirt_store",
          "label": "t-shirt store"
        },
        {
          "code": "tabascan_restaurant",
          "label": "tabascan restaurant"
        },
        {
          "code": "table_tennis_club",
          "label": "table tennis club"
        },
        {
          "code": "table_tennis_facility",
          "label": "table tennis facility"
        },
        {
          "code": "table_tennis_supply_store",
          "label": "table tennis supply store"
        },
        {
          "code": "tack_shop",
          "label": "tack shop"
        },
        {
          "code": "taco_restaurant",
          "label": "taco restaurant"
        },
        {
          "code": "tae_kwon_do_comp_area",
          "label": "taekwondo competition area"
        },
        {
          "code": "taekwondo_school",
          "label": "taekwondo school"
        },
        {
          "code": "tag_agency",
          "label": "tag agency"
        },
        {
          "code": "tai_chi_school",
          "label": "tai chi school"
        },
        {
          "code": "tailor",
          "label": "tailor"
        },
        {
          "code": "taiwanese_restaurant",
          "label": "taiwanese restaurant"
        },
        {
          "code": "takoyaki_stand",
          "label": "takoyaki restaurant"
        },
        {
          "code": "talent_agency",
          "label": "talent agency"
        },
        {
          "code": "tamale_shop",
          "label": "tamale shop"
        },
        {
          "code": "tannery",
          "label": "tannery"
        },
        {
          "code": "tanning_studio",
          "label": "tanning salon"
        },
        {
          "code": "taoist_temple",
          "label": "taoist temple"
        },
        {
          "code": "tapas_bar",
          "label": "tapas bar"
        },
        {
          "code": "tapas_restaurant",
          "label": "tapas restaurant"
        },
        {
          "code": "tatami_store",
          "label": "tatami store"
        },
        {
          "code": "tattoo_and_piercing_shop",
          "label": "tattoo and piercing shop"
        },
        {
          "code": "tattoo_removal_service",
          "label": "tattoo removal service"
        },
        {
          "code": "tattoo_shop",
          "label": "tattoo shop"
        },
        {
          "code": "tax_assessor",
          "label": "tax assessor"
        },
        {
          "code": "tax_attorney",
          "label": "tax attorney"
        },
        {
          "code": "tax_collectors_office",
          "label": "tax collector's office"
        },
        {
          "code": "tax_consultant",
          "label": "tax consultant"
        },
        {
          "code": "tax_department",
          "label": "tax department"
        },
        {
          "code": "tax_preparation",
          "label": "tax preparation"
        },
        {
          "code": "tax_preparation_service",
          "label": "tax preparation service"
        },
        {
          "code": "taxi_service",
          "label": "taxi service"
        },
        {
          "code": "taxi_stand",
          "label": "taxi stand"
        },
        {
          "code": "taxidermist",
          "label": "taxidermist"
        },
        {
          "code": "tb_clinic",
          "label": "tb clinic"
        },
        {
          "code": "tea_exporter",
          "label": "tea exporter"
        },
        {
          "code": "tea_house",
          "label": "tea house"
        },
        {
          "code": "tea_manufacturer",
          "label": "tea manufacturer"
        },
        {
          "code": "tea_market_place",
          "label": "tea market place"
        },
        {
          "code": "tea_store",
          "label": "tea store"
        },
        {
          "code": "tea_wholesaler",
          "label": "tea wholesaler"
        },
        {
          "code": "teacher_college",
          "label": "teacher college"
        },
        {
          "code": "technical_school",
          "label": "technical school"
        },
        {
          "code": "technical_service",
          "label": "technical service"
        },
        {
          "code": "technical_university",
          "label": "technical university"
        },
        {
          "code": "technology_museum",
          "label": "technology museum"
        },
        {
          "code": "technology_park",
          "label": "technology park"
        },
        {
          "code": "teeth_whitening_service",
          "label": "teeth whitening service"
        },
        {
          "code": "telecommunication_school",
          "label": "telecommunication school"
        },
        {
          "code": "telecommunications_contractor",
          "label": "telecommunications contractor"
        },
        {
          "code": "telecommunications_engineer",
          "label": "telecommunications engineer"
        },
        {
          "code": "telecommunications_equipment_supplier",
          "label": "telecommunications equipment supplier"
        },
        {
          "code": "telecommunications_service_provider",
          "label": "telecommunications service provider"
        },
        {
          "code": "telemarketing_service",
          "label": "telemarketing service"
        },
        {
          "code": "telephone_answering_service",
          "label": "telephone answering service"
        },
        {
          "code": "telephone_company",
          "label": "telephone company"
        },
        {
          "code": "telephone_exchange",
          "label": "telephone exchange"
        },
        {
          "code": "telescope_store",
          "label": "telescope store"
        },
        {
          "code": "television_repair_service",
          "label": "television repair service"
        },
        {
          "code": "television_station",
          "label": "television station"
        },
        {
          "code": "temp_agency",
          "label": "temp agency"
        },
        {
          "code": "tempura_bowl_restaurants",
          "label": "tempura donburi restaurant"
        },
        {
          "code": "tempura_dish_restaurant",
          "label": "tempura restaurant"
        },
        {
          "code": "tenant_ownership",
          "label": "tenant ownership"
        },
        {
          "code": "tenants_union",
          "label": "tenant's union"
        },
        {
          "code": "tennis_club",
          "label": "tennis club"
        },
        {
          "code": "tennis_court",
          "label": "tennis court"
        },
        {
          "code": "tennis_court_construction_company",
          "label": "tennis court construction company"
        },
        {
          "code": "tennis_instructor",
          "label": "tennis instructor"
        },
        {
          "code": "tennis_store",
          "label": "tennis store"
        },
        {
          "code": "tent_rental_service",
          "label": "tent rental service"
        },
        {
          "code": "teppan_grill_restaurant",
          "label": "teppanyaki restaurant"
        },
        {
          "code": "tesla_showroom",
          "label": "tesla showroom"
        },
        {
          "code": "tex_mex_restaurant",
          "label": "tex-mex restaurant"
        },
        {
          "code": "textile_engineer",
          "label": "textile engineer"
        },
        {
          "code": "textile_exporter",
          "label": "textile exporter"
        },
        {
          "code": "textile_mill",
          "label": "textile mill"
        },
        {
          "code": "thai_massage_therapist",
          "label": "thai massage therapist"
        },
        {
          "code": "thai_restaurant",
          "label": "thai restaurant"
        },
        {
          "code": "theater_company",
          "label": "theater company"
        },
        {
          "code": "theater_production",
          "label": "theater production"
        },
        {
          "code": "theater_supply_store",
          "label": "theater supply store"
        },
        {
          "code": "theatrical_costume_supplier",
          "label": "theatrical costume supplier"
        },
        {
          "code": "theme_park",
          "label": "theme park"
        },
        {
          "code": "thermal_baths",
          "label": "thermal baths"
        },
        {
          "code": "thermal_energy_company",
          "label": "thermal energy company"
        },
        {
          "code": "thread_supplier",
          "label": "thread supplier"
        },
        {
          "code": "threads_and_yarns_wholesaler",
          "label": "threads and yarns wholesaler"
        },
        {
          "code": "thrift_store",
          "label": "thrift store"
        },
        {
          "code": "tiki_bar",
          "label": "tiki bar"
        },
        {
          "code": "tile_contractor",
          "label": "tile contractor"
        },
        {
          "code": "tile_manufacturer",
          "label": "tile manufacturer"
        },
        {
          "code": "tile_store",
          "label": "tile store"
        },
        {
          "code": "time_and_temperature_announcement_service",
          "label": "time and temperature announcement service"
        },
        {
          "code": "timeshare_agency",
          "label": "timeshare agency"
        },
        {
          "code": "tire_manufacturer",
          "label": "tyre manufacturer"
        },
        {
          "code": "tire_shop",
          "label": "tire shop"
        },
        {
          "code": "title_company",
          "label": "title company"
        },
        {
          "code": "tobacco_exporter",
          "label": "tobacco exporter"
        },
        {
          "code": "tobacco_shop",
          "label": "tobacco shop"
        },
        {
          "code": "tobacco_supplier",
          "label": "tobacco supplier"
        },
        {
          "code": "tofu_restaurant",
          "label": "tofu restaurant"
        },
        {
          "code": "tofu_shop",
          "label": "tofu shop"
        },
        {
          "code": "toiletries_store",
          "label": "toiletries store"
        },
        {
          "code": "toll_road_rest_stop",
          "label": "toll road rest stop"
        },
        {
          "code": "toll_station",
          "label": "toll booth"
        },
        {
          "code": "toner_cartridge_supplier",
          "label": "toner cartridge supplier"
        },
        {
          "code": "tongue_restaurant",
          "label": "tongue restaurant"
        },
        {
          "code": "tonkatsu_restaurant",
          "label": "tonkatsu restaurant"
        },
        {
          "code": "tool_and_die_shop",
          "label": "tool & die shop"
        },
        {
          "code": "tool_grinding_service",
          "label": "tool grinding service"
        },
        {
          "code": "tool_manufacturer",
          "label": "tool manufacturer"
        },
        {
          "code": "tool_rental_service",
          "label": "tool rental service"
        },
        {
          "code": "tool_repair_shop",
          "label": "tool repair shop"
        },
        {
          "code": "tool_store",
          "label": "tool store"
        },
        {
          "code": "tool_wholesaler",
          "label": "tool wholesaler"
        },
        {
          "code": "toolroom",
          "label": "toolroom"
        },
        {
          "code": "topography_company",
          "label": "topography company"
        },
        {
          "code": "topsoil_supplier",
          "label": "topsoil supplier"
        },
        {
          "code": "tour_agency",
          "label": "tour agency"
        },
        {
          "code": "tour_operator",
          "label": "tour operator"
        },
        {
          "code": "tourist_attraction",
          "label": "tourist attraction"
        },
        {
          "code": "tourist_information_center",
          "label": "tourist information center"
        },
        {
          "code": "tower_communication_service",
          "label": "tower communication service"
        },
        {
          "code": "towing_equipment_provider",
          "label": "towing equipment provider"
        },
        {
          "code": "towing_service",
          "label": "towing service"
        },
        {
          "code": "townhouse_complex",
          "label": "townhouse complex"
        },
        {
          "code": "toy_and_game_manufacturer",
          "label": "toy and game manufacturer"
        },
        {
          "code": "toy_library",
          "label": "toy library"
        },
        {
          "code": "toy_manufacturer",
          "label": "toy manufacturer"
        },
        {
          "code": "toy_museum",
          "label": "toy museum"
        },
        {
          "code": "toy_store",
          "label": "toy store"
        },
        {
          "code": "toyota_dealer",
          "label": "toyota dealer"
        },
        {
          "code": "tractor_dealer",
          "label": "tractor dealer"
        },
        {
          "code": "tractor_repair_shop",
          "label": "tractor repair shop"
        },
        {
          "code": "trade_fair_construction_company",
          "label": "trade fair construction company"
        },
        {
          "code": "trade_school",
          "label": "trade school"
        },
        {
          "code": "trading_card_store",
          "label": "trading card store"
        },
        {
          "code": "traditional_costume_club",
          "label": "traditional costume club"
        },
        {
          "code": "traditional_kostume_store",
          "label": "traditional kostume store"
        },
        {
          "code": "traditional_market",
          "label": "traditional market"
        },
        {
          "code": "traditional_restaurant",
          "label": "traditional restaurant"
        },
        {
          "code": "traditional_teahouse",
          "label": "traditional teahouse"
        },
        {
          "code": "traditional_us_american_restaurant",
          "label": "traditional american restaurant"
        },
        {
          "code": "traffic_officer",
          "label": "traffic officer"
        },
        {
          "code": "trailer_dealer",
          "label": "trailer dealer"
        },
        {
          "code": "trailer_manufacturer",
          "label": "trailer manufacturer"
        },
        {
          "code": "trailer_rental_service",
          "label": "trailer rental service"
        },
        {
          "code": "trailer_repair_shop",
          "label": "trailer repair shop"
        },
        {
          "code": "trailer_supply_store",
          "label": "trailer supply store"
        },
        {
          "code": "train_depot",
          "label": "train depot"
        },
        {
          "code": "train_repairing_center",
          "label": "train repairing center"
        },
        {
          "code": "train_ticket_agency",
          "label": "train ticket agency"
        },
        {
          "code": "train_ticket_counter",
          "label": "train ticket counter"
        },
        {
          "code": "train_yard",
          "label": "train yard"
        },
        {
          "code": "training_center",
          "label": "training centre"
        },
        {
          "code": "training_school",
          "label": "training school"
        },
        {
          "code": "transcription_service",
          "label": "transcription service"
        },
        {
          "code": "transit_depot",
          "label": "transit depot"
        },
        {
          "code": "translator",
          "label": "translator"
        },
        {
          "code": "transmission_shop",
          "label": "transmission shop"
        },
        {
          "code": "transportation_escort_service",
          "label": "transportation escort service"
        },
        {
          "code": "transportation_service",
          "label": "transportation service"
        },
        {
          "code": "travel_agency",
          "label": "travel agency"
        },
        {
          "code": "travel_clinic",
          "label": "travel clinic"
        },
        {
          "code": "travel_lounge",
          "label": "travel lounge"
        },
        {
          "code": "travellers_lodge",
          "label": "travellers lodge"
        },
        {
          "code": "tree_farm",
          "label": "tree farm"
        },
        {
          "code": "tree_service",
          "label": "tree service"
        },
        {
          "code": "trial_attorney",
          "label": "trial attorney"
        },
        {
          "code": "tribal_headquarters",
          "label": "tribal headquarters"
        },
        {
          "code": "triumph_motorcycle_dealer",
          "label": "triumph motorcycle dealer"
        },
        {
          "code": "trophy_shop",
          "label": "trophy shop"
        },
        {
          "code": "tropical_fish_store",
          "label": "tropical fish store"
        },
        {
          "code": "truck_accessories_store",
          "label": "truck accessories store"
        },
        {
          "code": "truck_dealer",
          "label": "truck dealer"
        },
        {
          "code": "truck_farmer",
          "label": "truck farmer"
        },
        {
          "code": "truck_parts_supplier",
          "label": "truck parts supplier"
        },
        {
          "code": "truck_rental_agency",
          "label": "truck rental agency"
        },
        {
          "code": "truck_repair_shop",
          "label": "truck repair shop"
        },
        {
          "code": "truck_stop",
          "label": "truck stop"
        },
        {
          "code": "truck_topper_supplier",
          "label": "truck topper supplier"
        },
        {
          "code": "trucking_company",
          "label": "trucking company"
        },
        {
          "code": "trucking_school",
          "label": "trucking school"
        },
        {
          "code": "truss_manufacturer",
          "label": "truss manufacturer"
        },
        {
          "code": "trust_bank",
          "label": "trust bank"
        },
        {
          "code": "tsukigime_parking_lot",
          "label": "tsukigime parking lot"
        },
        {
          "code": "tune_up_supplier",
          "label": "tune up supplier"
        },
        {
          "code": "tuning_automobile",
          "label": "tuning automobile"
        },
        {
          "code": "tunisian_restaurant",
          "label": "tunisian restaurant"
        },
        {
          "code": "turf_supplier",
          "label": "turf supplier"
        },
        {
          "code": "turkish_restaurant",
          "label": "turkish restaurant"
        },
        {
          "code": "turkmen_restaurant",
          "label": "turkmen restaurant"
        },
        {
          "code": "turnery",
          "label": "turnery"
        },
        {
          "code": "tuscan_restaurant",
          "label": "tuscan restaurant"
        },
        {
          "code": "tutoring_service",
          "label": "tutoring service"
        },
        {
          "code": "tuxedo_shop",
          "label": "tuxedo shop"
        },
        {
          "code": "typewriter_repair_service",
          "label": "typewriter repair service"
        },
        {
          "code": "typewriter_supplier",
          "label": "typewriter supplier"
        },
        {
          "code": "typing_service",
          "label": "typing service"
        },
        {
          "code": "udon_noodle_shop",
          "label": "udon noodle restaurant"
        },
        {
          "code": "ukrainian_restaurant",
          "label": "ukrainian restaurant"
        },
        {
          "code": "unagi_restaurant",
          "label": "unagi restaurant"
        },
        {
          "code": "underwear_store",
          "label": "underwear store"
        },
        {
          "code": "unemployment_office",
          "label": "unemployment office"
        },
        {
          "code": "unfinished_furniture_store",
          "label": "unfinished furniture store"
        },
        {
          "code": "uniform_store",
          "label": "uniform store"
        },
        {
          "code": "unisex_hairdresser",
          "label": "hairdresser"
        },
        {
          "code": "unitarian_universalist_church",
          "label": "unitarian universalist church"
        },
        {
          "code": "united_church_of_canada",
          "label": "united church of canada"
        },
        {
          "code": "united_church_of_christ",
          "label": "united church of christ"
        },
        {
          "code": "united_methodist_church",
          "label": "united methodist church"
        },
        {
          "code": "united_states_armed_forces_base",
          "label": "united states armed forces base"
        },
        {
          "code": "unity_church",
          "label": "unity church"
        },
        {
          "code": "university",
          "label": "university"
        },
        {
          "code": "university_department",
          "label": "university department"
        },
        {
          "code": "university_hospital",
          "label": "university hospital"
        },
        {
          "code": "university_library",
          "label": "university library"
        },
        {
          "code": "upholstery_cleaning_service",
          "label": "upholstery cleaning service"
        },
        {
          "code": "upholstery_shop",
          "label": "upholstery shop"
        },
        {
          "code": "urban_planning_department",
          "label": "urban planning department"
        },
        {
          "code": "urgent_care_center",
          "label": "urgent care center"
        },
        {
          "code": "urologist",
          "label": "urologist"
        },
        {
          "code": "urology_clinic",
          "label": "urology clinic"
        },
        {
          "code": "uruguayan_restaurant",
          "label": "uruguayan restaurant"
        },
        {
          "code": "us_pacific_northwest_restaurant",
          "label": "pacific northwest restaurant (us)"
        },
        {
          "code": "used_appliance_store",
          "label": "used appliance store"
        },
        {
          "code": "used_auto_parts_store",
          "label": "used auto parts store"
        },
        {
          "code": "used_bicycle_shop",
          "label": "used bicycle shop"
        },
        {
          "code": "used_book_store",
          "label": "used book store"
        },
        {
          "code": "used_car_dealer",
          "label": "used car dealer"
        },
        {
          "code": "used_cd_store",
          "label": "used cd store"
        },
        {
          "code": "used_clothing_store",
          "label": "used clothing store"
        },
        {
          "code": "used_computer_store",
          "label": "used computer store"
        },
        {
          "code": "used_furniture_store",
          "label": "used furniture store"
        },
        {
          "code": "used_game_store",
          "label": "used game store"
        },
        {
          "code": "used_motorcycle_dealer",
          "label": "used motorcycle dealer"
        },
        {
          "code": "used_musical_instrument_store",
          "label": "used musical instrument store"
        },
        {
          "code": "used_office_furniture_store",
          "label": "used office furniture store"
        },
        {
          "code": "used_store_fixture_supplier",
          "label": "used store fixture supplier"
        },
        {
          "code": "used_tire_shop",
          "label": "used tire shop"
        },
        {
          "code": "used_truck_dealer",
          "label": "used truck dealer"
        },
        {
          "code": "utility_contractor",
          "label": "utility contractor"
        },
        {
          "code": "utility_trailer_dealer",
          "label": "utility trailer dealer"
        },
        {
          "code": "uzbek_restaurant",
          "label": "uzbeki restaurant"
        },
        {
          "code": "vacation_appartment",
          "label": "holiday apartment"
        },
        {
          "code": "vacation_home_rental_agency",
          "label": "vacation home rental agency"
        },
        {
          "code": "vacuum_cleaner_repair_shop",
          "label": "vacuum cleaner repair shop"
        },
        {
          "code": "vacuum_cleaner_store",
          "label": "vacuum cleaner store"
        },
        {
          "code": "vacuum_cleaning_system_supplier",
          "label": "vacuum cleaning system supplier"
        },
        {
          "code": "valencian_restaurant",
          "label": "valencian restaurant"
        },
        {
          "code": "valet_parking_service",
          "label": "valet parking service"
        },
        {
          "code": "van_rental_agency",
          "label": "van rental agency"
        },
        {
          "code": "vaporizer_store",
          "label": "vaporizer store"
        },
        {
          "code": "variety_store",
          "label": "variety store"
        },
        {
          "code": "vascular_surgeon",
          "label": "vascular surgeon"
        },
        {
          "code": "vastu_consultant",
          "label": "vastu consultant"
        },
        {
          "code": "vcr_repair_service",
          "label": "vcr repair service"
        },
        {
          "code": "vegan_restaurant",
          "label": "vegan restaurant"
        },
        {
          "code": "vegetable_wholesale_market",
          "label": "vegetable wholesale market"
        },
        {
          "code": "vegetable_wholesaler",
          "label": "vegetable wholesaler"
        },
        {
          "code": "vegetarian_cafe_and_deli",
          "label": "vegetarian cafe and deli"
        },
        {
          "code": "vegetarian_restaurant",
          "label": "vegetarian restaurant"
        },
        {
          "code": "vehicle_examination_office",
          "label": "vehicle examination office"
        },
        {
          "code": "vehicle_exporter",
          "label": "vehicle exporter"
        },
        {
          "code": "vehicle_inspection",
          "label": "vehicle inspection"
        },
        {
          "code": "vehicle_shipping_agent",
          "label": "vehicle shipping agent"
        },
        {
          "code": "velodrome",
          "label": "velodrome"
        },
        {
          "code": "vending_machine_supplier",
          "label": "vending machine supplier"
        },
        {
          "code": "venereologist",
          "label": "venereologist"
        },
        {
          "code": "venetian_restaurant",
          "label": "venetian restaurant"
        },
        {
          "code": "venezuelan_restaurant",
          "label": "venezuelan restaurant"
        },
        {
          "code": "ventilating_equipment_manufacturer",
          "label": "ventilating equipment manufacturer"
        },
        {
          "code": "venture_capital_company",
          "label": "venture capital company"
        },
        {
          "code": "veterans_affairs_department",
          "label": "veterans affairs department"
        },
        {
          "code": "veterans_center",
          "label": "veterans center"
        },
        {
          "code": "veterans_hospital",
          "label": "veterans hospital"
        },
        {
          "code": "veterans_organization",
          "label": "veterans organization"
        },
        {
          "code": "veterinarian",
          "label": "veterinarian"
        },
        {
          "code": "veterinary_pharmacy",
          "label": "veterinary pharmacy"
        },
        {
          "code": "video_arcade",
          "label": "video arcade"
        },
        {
          "code": "video_camera_repair_service",
          "label": "video camera repair service"
        },
        {
          "code": "video_conferencing_equipment_supplier",
          "label": "video conferencing equipment supplier"
        },
        {
          "code": "video_conferencing_service",
          "label": "video conferencing service"
        },
        {
          "code": "video_duplication_service",
          "label": "video duplication service"
        },
        {
          "code": "video_editing_service",
          "label": "video editing service"
        },
        {
          "code": "video_equipment_repair_service",
          "label": "video equipment repair service"
        },
        {
          "code": "video_game_rental_kiosk",
          "label": "video game rental kiosk"
        },
        {
          "code": "video_game_rental_service",
          "label": "video game rental service"
        },
        {
          "code": "video_game_rental_store",
          "label": "video game rental store"
        },
        {
          "code": "video_game_store",
          "label": "video game store"
        },
        {
          "code": "video_karaoke",
          "label": "video karaoke"
        },
        {
          "code": "video_production_service",
          "label": "video production service"
        },
        {
          "code": "video_store",
          "label": "video store"
        },
        {
          "code": "vietnamese_restaurant",
          "label": "vietnamese restaurant"
        },
        {
          "code": "villa",
          "label": "villa"
        },
        {
          "code": "village_hall",
          "label": "village hall"
        },
        {
          "code": "vineyard",
          "label": "vineyard"
        },
        {
          "code": "vineyard_church",
          "label": "vineyard church"
        },
        {
          "code": "vintage_clothing_store",
          "label": "vintage clothing store"
        },
        {
          "code": "violin_shop",
          "label": "violin shop"
        },
        {
          "code": "virtual_office_rental",
          "label": "virtual office rental"
        },
        {
          "code": "visa_and_passport_office",
          "label": "visa and passport office"
        },
        {
          "code": "visa_consultant",
          "label": "visa consultant"
        },
        {
          "code": "visitor_center",
          "label": "visitor center"
        },
        {
          "code": "vitamin_and_supplements_store",
          "label": "vitamin & supplements store"
        },
        {
          "code": "vocal_instructor",
          "label": "vocal instructor"
        },
        {
          "code": "vocational_college",
          "label": "vocational college"
        },
        {
          "code": "vocational_school_one",
          "label": "vocational school one"
        },
        {
          "code": "vocational_training_school",
          "label": "vocational school"
        },
        {
          "code": "volkswagen_dealer",
          "label": "volkswagen dealer"
        },
        {
          "code": "volleyball_club",
          "label": "volleyball club"
        },
        {
          "code": "volleyball_court",
          "label": "volleyball court"
        },
        {
          "code": "volleyball_instructor",
          "label": "volleyball instructor"
        },
        {
          "code": "volunteer_organization",
          "label": "volunteer organization"
        },
        {
          "code": "volvo_dealer",
          "label": "volvo dealer"
        },
        {
          "code": "voter_registration_office",
          "label": "voter registration office"
        },
        {
          "code": "waldorf_kindergarten",
          "label": "waldorf kindergarten"
        },
        {
          "code": "waldorf_school",
          "label": "waldorf school"
        },
        {
          "code": "walk_in_clinic",
          "label": "walk-in clinic"
        },
        {
          "code": "wallpaper_store",
          "label": "wallpaper store"
        },
        {
          "code": "war_museum",
          "label": "war museum"
        },
        {
          "code": "warehouse",
          "label": "warehouse"
        },
        {
          "code": "warehouse_club",
          "label": "warehouse club"
        },
        {
          "code": "warehouse_store",
          "label": "warehouse store"
        },
        {
          "code": "washer_and_dryer_repair_service",
          "label": "washer & dryer repair service"
        },
        {
          "code": "washer_and_dryer_store",
          "label": "washer & dryer store"
        },
        {
          "code": "waste_management_service",
          "label": "waste management service"
        },
        {
          "code": "watch_manufacturer",
          "label": "watch manufacturer"
        },
        {
          "code": "watch_repair_service",
          "label": "watch repair service"
        },
        {
          "code": "watch_store",
          "label": "watch store"
        },
        {
          "code": "water_cooler_supplier",
          "label": "water cooler supplier"
        },
        {
          "code": "water_damage_restoration_service",
          "label": "water damage restoration service"
        },
        {
          "code": "water_filter_supplier",
          "label": "water filter supplier"
        },
        {
          "code": "water_jet_cutting_service",
          "label": "water jet cutting service"
        },
        {
          "code": "water_mill",
          "label": "water mill"
        },
        {
          "code": "water_park",
          "label": "water park"
        },
        {
          "code": "water_polo_pool",
          "label": "water polo pool"
        },
        {
          "code": "water_pump_supplier",
          "label": "water pump supplier"
        },
        {
          "code": "water_purification_company",
          "label": "water purification company"
        },
        {
          "code": "water_ski_shop",
          "label": "water ski shop"
        },
        {
          "code": "water_skiing_club",
          "label": "water skiing club"
        },
        {
          "code": "water_skiing_instructor",
          "label": "water skiing instructor"
        },
        {
          "code": "water_skiing_service",
          "label": "water skiing service"
        },
        {
          "code": "water_softening_equipment_supplier",
          "label": "water softening equipment supplier"
        },
        {
          "code": "water_sports_equipment_rental_service",
          "label": "water sports equipment rental service"
        },
        {
          "code": "water_tank_cleaning_service",
          "label": "water tank cleaning service"
        },
        {
          "code": "water_testing_service",
          "label": "water testing service"
        },
        {
          "code": "water_treatment_plant",
          "label": "water treatment plant"
        },
        {
          "code": "water_treatment_supplier",
          "label": "water treatment supplier"
        },
        {
          "code": "water_utility_company",
          "label": "water utility company"
        },
        {
          "code": "water_works",
          "label": "water works"
        },
        {
          "code": "water_works_equipment_supplier",
          "label": "water works equipment supplier"
        },
        {
          "code": "waterbed_repair_service",
          "label": "waterbed repair service"
        },
        {
          "code": "waterbed_store",
          "label": "waterbed store"
        },
        {
          "code": "waterproofing_company",
          "label": "waterproofing company"
        },
        {
          "code": "wax_museum",
          "label": "wax museum"
        },
        {
          "code": "wax_supplier",
          "label": "wax supplier"
        },
        {
          "code": "waxing_hair_removal_service",
          "label": "waxing hair removal service"
        },
        {
          "code": "weather_forecast_service",
          "label": "weather forecast service"
        },
        {
          "code": "weaving_mill",
          "label": "weaving mill"
        },
        {
          "code": "web_hosting_service",
          "label": "web hosting company"
        },
        {
          "code": "website_designer",
          "label": "website designer"
        },
        {
          "code": "wedding_bakery",
          "label": "wedding bakery"
        },
        {
          "code": "wedding_buffet",
          "label": "wedding buffet"
        },
        {
          "code": "wedding_chapel",
          "label": "wedding chapel"
        },
        {
          "code": "wedding_dress_rental_service",
          "label": "wedding dress rental service"
        },
        {
          "code": "wedding_photographer",
          "label": "wedding photographer"
        },
        {
          "code": "wedding_planner",
          "label": "wedding planner"
        },
        {
          "code": "wedding_service",
          "label": "wedding service"
        },
        {
          "code": "wedding_souvenir_shop",
          "label": "wedding souvenir shop"
        },
        {
          "code": "wedding_store",
          "label": "wedding store"
        },
        {
          "code": "wedding_venue",
          "label": "wedding venue"
        },
        {
          "code": "weigh_station",
          "label": "weigh station"
        },
        {
          "code": "weight_loss_service",
          "label": "weight loss service"
        },
        {
          "code": "weightlifting_area",
          "label": "weightlifting area"
        },
        {
          "code": "weir",
          "label": "weir"
        },
        {
          "code": "welder",
          "label": "welder"
        },
        {
          "code": "welding_gas_supplier",
          "label": "welding gas supplier"
        },
        {
          "code": "welding_supply_store",
          "label": "welding supply store"
        },
        {
          "code": "well_drilling_contractor",
          "label": "well drilling contractor"
        },
        {
          "code": "wellness_center",
          "label": "wellness center"
        },
        {
          "code": "wellness_hotel",
          "label": "wellness hotel"
        },
        {
          "code": "wellness_program",
          "label": "wellness program"
        },
        {
          "code": "welsh_restaurant",
          "label": "welsh restaurant"
        },
        {
          "code": "wesleyan_church",
          "label": "wesleyan church"
        },
        {
          "code": "west_african_restaurant",
          "label": "west african restaurant"
        },
        {
          "code": "western_apparel_store",
          "label": "western apparel store"
        },
        {
          "code": "western_restaurant",
          "label": "western restaurant"
        },
        {
          "code": "whale_watching_tour_agency",
          "label": "whale watching tour agency"
        },
        {
          "code": "wheel_alignment_service",
          "label": "wheel alignment service"
        },
        {
          "code": "wheel_store",
          "label": "wheel store"
        },
        {
          "code": "wheelchair_rental_service",
          "label": "wheelchair rental service"
        },
        {
          "code": "wheelchair_repair_service",
          "label": "wheelchair repair service"
        },
        {
          "code": "wheelchair_store",
          "label": "wheelchair store"
        },
        {
          "code": "wholesale_bakery",
          "label": "wholesale bakery"
        },
        {
          "code": "wholesale_drugstore",
          "label": "wholesale drugstore"
        },
        {
          "code": "wholesale_florist",
          "label": "wholesale florist"
        },
        {
          "code": "wholesale_food_store",
          "label": "wholesale food store"
        },
        {
          "code": "wholesale_grocer",
          "label": "wholesale grocer"
        },
        {
          "code": "wholesale_jeweler",
          "label": "wholesale jeweler"
        },
        {
          "code": "wholesale_market",
          "label": "wholesale market"
        },
        {
          "code": "wholesale_plant_nursery",
          "label": "wholesale plant nursery"
        },
        {
          "code": "wholesaler",
          "label": "wholesaler"
        },
        {
          "code": "wholesaler_household_appliances",
          "label": "wholesaler household appliances"
        },
        {
          "code": "wi_fi_spot",
          "label": "wi-fi spot"
        },
        {
          "code": "wicker_store",
          "label": "wicker store"
        },
        {
          "code": "wig_shop",
          "label": "wig shop"
        },
        {
          "code": "wildlife_and_safari_park",
          "label": "wildlife and safari park"
        },
        {
          "code": "wildlife_park",
          "label": "wildlife park"
        },
        {
          "code": "wildlife_refuge",
          "label": "wildlife refuge"
        },
        {
          "code": "wildlife_rescue_service",
          "label": "wildlife rescue service"
        },
        {
          "code": "willow_basket_manufacturer",
          "label": "willow basket manufacturer"
        },
        {
          "code": "wind_farm",
          "label": "wind farm"
        },
        {
          "code": "wind_turbine_builder",
          "label": "wind turbine builder"
        },
        {
          "code": "window_cleaning_service",
          "label": "window cleaning service"
        },
        {
          "code": "window_installation_service",
          "label": "window installation service"
        },
        {
          "code": "window_supplier",
          "label": "window supplier"
        },
        {
          "code": "window_tinting_service",
          "label": "window tinting service"
        },
        {
          "code": "window_treatment_store",
          "label": "window treatment store"
        },
        {
          "code": "windsurfing_store",
          "label": "windsurfing store"
        },
        {
          "code": "wine_bar",
          "label": "wine bar"
        },
        {
          "code": "wine_cellar",
          "label": "wine cellar"
        },
        {
          "code": "wine_club",
          "label": "wine club"
        },
        {
          "code": "wine_storage_facility",
          "label": "wine storage facility"
        },
        {
          "code": "wine_store",
          "label": "wine store"
        },
        {
          "code": "wine_wholesaler",
          "label": "wine wholesaler and importer"
        },
        {
          "code": "winemaking_supply_store",
          "label": "winemaking supply store"
        },
        {
          "code": "winery",
          "label": "winery"
        },
        {
          "code": "wing_chun_school",
          "label": "wing chun school"
        },
        {
          "code": "wok_restaurant",
          "label": "wok restaurant"
        },
        {
          "code": "womens_clothing_store",
          "label": "women's clothing store"
        },
        {
          "code": "womens_college",
          "label": "womens college"
        },
        {
          "code": "womens_organization",
          "label": "women's organization"
        },
        {
          "code": "womens_personal_trainer",
          "label": "womens personal trainer"
        },
        {
          "code": "womens_protection_service",
          "label": "womens protection service"
        },
        {
          "code": "womens_shelter",
          "label": "women's shelter"
        },
        {
          "code": "wood_and_laminate_flooring_supplier",
          "label": "wood and laminate flooring supplier"
        },
        {
          "code": "wood_floor_installation_service",
          "label": "wood floor installation service"
        },
        {
          "code": "wood_floor_refinishing_service",
          "label": "wood floor refinishing service"
        },
        {
          "code": "wood_frame_supplier",
          "label": "wood frame supplier"
        },
        {
          "code": "wood_stove_shop",
          "label": "wood stove shop"
        },
        {
          "code": "wood_supplier",
          "label": "wood supplier"
        },
        {
          "code": "wood_working_class",
          "label": "wood working class"
        },
        {
          "code": "woodworker",
          "label": "woodworker"
        },
        {
          "code": "woodworking_supply_store",
          "label": "woodworking supply store"
        },
        {
          "code": "wool_store",
          "label": "wool store"
        },
        {
          "code": "work_clothes_store",
          "label": "work clothes store"
        },
        {
          "code": "workers_club",
          "label": "workers' club"
        },
        {
          "code": "working_womens_hostel",
          "label": "working womens hostel"
        },
        {
          "code": "wrestling_school",
          "label": "wrestling school"
        },
        {
          "code": "x_ray_equipment_supplier",
          "label": "x-ray equipment supplier"
        },
        {
          "code": "x_ray_lab",
          "label": "x-ray lab"
        },
        {
          "code": "yacht_broker",
          "label": "yacht broker"
        },
        {
          "code": "yacht_club",
          "label": "yacht club"
        },
        {
          "code": "yakatabune",
          "label": "yakatabune"
        },
        {
          "code": "yakiniku_restaurant",
          "label": "yakiniku restaurant"
        },
        {
          "code": "yakitori_restaurant",
          "label": "yakitori restaurant"
        },
        {
          "code": "yamaha_motorcycle_dealer",
          "label": "yamaha motorcycle dealer"
        },
        {
          "code": "yarn_store",
          "label": "yarn store"
        },
        {
          "code": "yemenite_restaurant",
          "label": "yemenite restaurant"
        },
        {
          "code": "yeshiva",
          "label": "yeshiva"
        },
        {
          "code": "yoga_instructor",
          "label": "yoga instructor"
        },
        {
          "code": "yoga_retreat_center",
          "label": "yoga retreat center"
        },
        {
          "code": "yoga_studio",
          "label": "yoga studio"
        },
        {
          "code": "youth_care",
          "label": "youth care"
        },
        {
          "code": "youth_center",
          "label": "youth center"
        },
        {
          "code": "youth_clothing_store",
          "label": "youth clothing store"
        },
        {
          "code": "youth_club",
          "label": "youth club"
        },
        {
          "code": "youth_groups",
          "label": "youth group"
        },
        {
          "code": "youth_hostel",
          "label": "youth hostel"
        },
        {
          "code": "youth_organization",
          "label": "youth organization"
        },
        {
          "code": "youth_social_services_organization",
          "label": "youth social services organization"
        },
        {
          "code": "yucatan_restaurant",
          "label": "yucatan restaurant"
        },
        {
          "code": "zac",
          "label": "zac"
        },
        {
          "code": "zhe_jiang_restaurant",
          "label": "zhejiang restaurant"
        },
        {
          "code": "zoo",
          "label": "zoo"
        }
      ]
};
