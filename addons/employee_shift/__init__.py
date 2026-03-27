# -*- coding: utf-8 -*-

from . import models


def employee_shift_post_init(cr, registry):
    # Safely alter the color column to text to accept hex values
    cr.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='employee_shift' AND column_name='color'
            ) THEN
                -- try to alter column type to text
                BEGIN
                    ALTER TABLE employee_shift ALTER COLUMN color TYPE text USING color::text;
                EXCEPTION WHEN others THEN
                    -- ignore any errors during migration
                    RAISE NOTICE 'employee_shift: could not alter color column: %', SQLERRM;
                END;
            END IF;
        END
        $$;
    """)
