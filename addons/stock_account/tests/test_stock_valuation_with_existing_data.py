# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestStockValuationWithExistingData(TransactionCase):

    def test_valuation_fifo_with_current_products(self):
        """ Test if the inventory valuation gives the same results using
            A. inventory valuation at current data
            B. inventory valuation in the past with current date specified
            Do it in SQL, it is faster
        """

        self.env.cr.execute("""
DO
$do$
DECLARE

	v_product_product_ids int[];
	v_stock_valuation_account int;
	v_company_id int;
	v_faulty_valuation_count int;
	v_faulty_product_products int[];

BEGIN

    -- Create temporary tables to limit complexity of queries and logic
    CREATE TABLE aml_valuation( product_id int, value float);
    CREATE TABLE sm_valuation( product_id int, value float);

    -- Loop on the different company_ids, and stock_valuation_ids for active products in fifo - realtime
    FOR  v_stock_valuation_account,v_company_id,v_product_product_ids IN
    SELECT
        COALESCE(p1.value_account, p1bis.value_account_default) account,
        COALESCE(p1.company_id, p1bis.company_id)company_id,
        array_agg(pp.id) pp_ids
    FROM product_product pp
    JOIN product_template pt on pt.id = pp.product_tmpl_id
    JOIN product_category pc on pc.id = pt.categ_id
    LEFT JOIN (SELECT CAST(split_part(res_id, ',', 2) as INTEGER) pc_id,
        CAST(split_part(value_reference, ',', 2) as INTEGER) value_account,*
        from ir_property ip_account where name = 'property_stock_valuation_account_id' )p1 on (p1.pc_id = pc.id and pt.company_id= p1.company_id)
    LEFT JOIN (SELECT CAST(split_part(value_reference, ',', 2) as INTEGER) value_account_default,*
        from ir_property ip_account where name = 'property_stock_valuation_account_id' and res_id is NULL order by id limit 1 )p1bis on (pt.company_id= p1bis.company_id)
    LEFT join (SELECT CAST(split_part(res_id, ',', 2) as INTEGER) pc_id,
        CAST(split_part(value_reference, ',', 2) as INTEGER) value_account,*
        from ir_property ip_account where name = 'property_cost_method'  and value_text = 'fifo' )p2 on (p2.pc_id = pc.id and pt.company_id= p2.company_id)
    LEFT join (SELECT CAST(split_part(res_id, ',', 2) as INTEGER) pc_id,
        CAST(split_part(value_reference, ',', 2) as INTEGER) value_account,*
        from ir_property ip_account where name = 'property_valuation'  and value_text = 'real_time' )p3 on (p3.pc_id = pc.id and pt.company_id= p3.company_id)
            WHERE pp.active = TRUE
            AND pt.active = TRUE
            AND pt.type='product'
    GROUP BY 1,2
    LOOP

        -- Insert in temporary tables
        INSERT INTO aml_valuation(product_id, value)
        SELECT aml.product_id, sum(balance) AS value
            FROM account_move_line AS aml
            WHERE aml.product_id =ANY(v_product_product_ids)
                    and aml.account_id=v_stock_valuation_account
                    and company_id =v_company_id
                    GROUP BY aml.product_id ;

        INSERT INTO sm_valuation(product_id, value)
        select product_id, sum(remaining_value) AS value
                    from (
                    SELECT "stock_move"."product_id" AS product_id, stock_move.remaining_qty, stock_move.remaining_value
                    FROM "stock_location" as "stock_move__location_id","stock_location" as "stock_move__location_dest_id","stock_move"
                    LEFT JOIN "stock_picking" as "stock_move__picking_id" ON ("stock_move"."picking_id" = "stock_move__picking_id"."id")
                    WHERE ("stock_move"."location_id"="stock_move__location_id"."id" AND "stock_move"."location_dest_id"="stock_move__location_dest_id"."id") AND
                        ((("stock_move"."product_id" =ANY(v_product_product_ids) )  AND  ("stock_move"."state" = 'done'))  AND
                            ((("stock_move__location_id"."company_id" IS NULL   OR  (("stock_move__location_id"."usage" in ('inventory','production'))
                            AND  ("stock_move__location_id"."company_id" = v_company_id)))  AND  ("stock_move__location_dest_id"."company_id" = v_company_id))  OR
                                (("stock_move__location_id"."company_id" = v_company_id)  AND  ("stock_move__location_dest_id"."company_id" IS NULL   OR
                                    (("stock_move__location_dest_id"."usage" = 'inventory')  AND  ("stock_move__location_dest_id"."company_id" = v_company_id)))))) -- amazing line made in ORM
                    )A
                    GROUP BY 1
                ;

	END LOOP;

    -- Check the result is correct
    SELECT count(*), array_agg(a.product_id) FROM sm_valuation s
    JOIN aml_valuation a ON s.product_id = a.product_id
    WHERE ABS(COALESCE(a.value,0) - COALESCE(s.value,0)) > 0.0001
    INTO v_faulty_valuation_count, v_faulty_product_products;

    IF v_faulty_valuation_count>0 THEN
        RAISE EXCEPTION 'Inconsistent inventory valuation for % product_product(s)', v_faulty_valuation_count
        USING HINT = 'Check the following product_products: '||substr(CAST(v_faulty_product_products AS varchar), 2, length(CAST(v_faulty_product_products AS varchar)) - 2);
    END IF;

end;
$do$;
""")
