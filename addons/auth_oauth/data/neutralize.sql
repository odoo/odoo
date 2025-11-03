-- disable oauth providers, except those listed in a JSON array stored
-- as ir.config_parameter with key 'auth_oauth.dont_neutralize_providers'.
-- If the parameter does not exist or is not a valid JSON array,
-- all providers will be disabled.
UPDATE auth_oauth_provider op
SET enabled = FALSE
WHERE op.id NOT IN (
    SELECT CAST(
        jsonb_array_elements(
            CAST(
                CASE WHEN jsonb_typeof(value::jsonb) = 'array' THEN value ELSE '[]' END
                AS JSONB
            )
        ) as INTEGER
    )
    AS id
    FROM ir_config_parameter
    WHERE key = 'auth_oauth.dont_neutralize_providers'
)
