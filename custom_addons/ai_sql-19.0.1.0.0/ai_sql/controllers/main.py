# -*- coding: utf-8 -*-
import json
import logging
import re
import openai
from datetime import datetime
import io # For Excel export
import xlsxwriter # For Excel export - needs to be installed: pip install XlsxWriter

from odoo import http, release
from odoo.http import request, route, content_disposition # For Excel download
from odoo.exceptions import UserError, AccessError

_logger = logging.getLogger(__name__)

# Backend URL is no longer needed as we call OpenAI directly
# BACKEND_TIMEOUT = 30 # Keep for OpenAI call timeout if needed

CORE_KEYWORD_MAP_SQL = {
    # Common Nouns -> Odoo Models
    'customer': 'res.partner', 'customers': 'res.partner',
    'contact': 'res.partner', 'contacts': 'res.partner',
    'partner': 'res.partner', 'partners': 'res.partner',
    'supplier': 'res.partner', 'suppliers': 'res.partner',
    'vendor': 'res.partner', 'vendors': 'res.partner',
    'company': 'res.company', 'companies': 'res.company', # Also res.partner depending on context
    'user': 'res.users', 'users': 'res.users',
    'employee': 'hr.employee', 'employees': 'hr.employee', # Requires hr module
    'product': 'product.product', 'products': 'product.product',
    'item': 'product.product', 'items': 'product.product',
    'service': 'product.product', 'services': 'product.product',
    'sale': 'sale.order', 'sales': 'sale.order',
    'order': 'sale.order', 'orders': 'sale.order',
    'quotation': 'sale.order', 'quotations': 'sale.order',
    'so': 'sale.order',
    'line': ['sale.order.line', 'account.move.line', 'purchase.order.line'], # Ambiguous, list possible
    'lines': ['sale.order.line', 'account.move.line', 'purchase.order.line'],
    'invoice': 'account.move', 'invoices': 'account.move',
    'bill': 'account.move', 'bills': 'account.move',
    'entry': 'account.move.line', 'entries': 'account.move.line', # Journal Entries
    'journal': ['account.journal', 'account.move.line'],
    'payment': 'account.payment', 'payments': 'account.payment',
    'bank': ['account.bank.statement', 'res.partner.bank'],
    'statement': 'account.bank.statement.line',
    'purchase': 'purchase.order', 'purchases': 'purchase.order',
    'po': 'purchase.order',
    'lead': 'crm.lead', 'leads': 'crm.lead', # Requires crm
    'opportunity': 'crm.lead', 'opportunities': 'crm.lead',
    'task': 'project.task', 'tasks': 'project.task', # Requires project
    'project': 'project.project', 'projects': 'project.project',
    'stock': ['stock.quant', 'product.product', 'stock.move'],
    'inventory': ['stock.quant', 'product.product', 'stock.inventory', 'stock.move'],
    'quantity': ['stock.quant', 'product.product', 'sale.order.line', 'purchase.order.line'],
    'move': ['stock.move', 'account.move'], 'moves': ['stock.move', 'account.move'],
    'location': 'stock.location', 'locations': 'stock.location',
    'warehouse': 'stock.warehouse', 'warehouses': 'stock.warehouse',
    'attribute': 'product.attribute', 'attributes': 'product.attribute',
    'value': 'product.attribute.value', 'values': 'product.attribute.value',
    'category': ['product.category', 'res.partner.category'], 'categories': ['product.category', 'res.partner.category'],
    'tag': 'crm.tag', 'tags': 'crm.tag', # Example, other tag models exist
    # ... Add more common terms ...
}
class AISQLGeneratorController(http.Controller):

    # --- _extract_relevant_models_for_sql (Simplified Placeholder) ---
    def _extract_relevant_models_for_sql(self, query_text):
        """
        Enhanced model identification for SQL context.
        1. Core keyword map to ORM models.
        2. Dynamic matching against `ir.model` names (human-readable descriptions).
        3. Explicit technical name matching (ORM like `sale.order` or SQL like `sale_order`).
        Returns a list of ORM model names.
        """
        query_lower = query_text.lower()
        # Extract words (e.g., >= 3 chars) and also full phrases if "quoted".
        # This regex captures words or quoted phrases.
        potential_keywords = set(re.findall(r'"[^"]+"|\b\w{3,}\b', query_lower))
        # Normalize quoted phrases by removing quotes and lowercasing.
        query_words = set()
        for pk in potential_keywords:
            if pk.startswith('"') and pk.endswith('"'):
                query_words.add(pk[1:-1])
            else:
                query_words.add(pk)

        _logger.info(f"SQL Model Extraction: Query words/phrases identified: {query_words}")

        # This set will store ORM model names (e.g., 'sale.order')
        relevant_orm_models = set()
        matched_from_query = set() # Track words already used to find models

        # --- Step 1: Apply Core Keyword Map (Keywords -> ORM Model Names) ---
        for keyword, orm_models_to_add in CORE_KEYWORD_MAP_SQL.items():
            if keyword in query_words:
                _logger.debug(f"CORE map match: Keyword '{keyword}' maps to {orm_models_to_add}")
                if isinstance(orm_models_to_add, list):
                    relevant_orm_models.update(m for m in orm_models_to_add if m in request.env)
                elif orm_models_to_add in request.env:
                    relevant_orm_models.add(orm_models_to_add)
                matched_from_query.add(keyword)

        # --- Step 2: Dynamic Matching (Tokens from Query Words -> Tokens from Model Human Names) ---
        remaining_words_for_dynamic_match = query_words - matched_from_query
        if remaining_words_for_dynamic_match:
            _logger.debug(f"Attempting dynamic model match for words: {remaining_words_for_dynamic_match}")
            try:
                all_system_models_info = request.env['ir.model'].search_read(
                    [('state', '=', 'base'), ('transient', '=', False)], # Only installed, non-transient
                    ['model', 'name'] # 'model' is technical (sale.order), 'name' is human (Sales Order)
                )
                for model_info in all_system_models_info:
                    model_orm_name = model_info.get('model')
                    model_human_name_lower = model_info.get('name', '').lower()
                    if not model_orm_name or not model_human_name_lower:
                        continue

                    # Tokenize the model's human name (e.g., "Sales Order" -> {"sales", "order"})
                    model_name_tokens = set(re.findall(r'\b\w{3,}\b', model_human_name_lower))

                    # Check if any of the user's query words match tokens from the model's human name
                    if remaining_words_for_dynamic_match.intersection(model_name_tokens):
                        if model_orm_name in request.env: # Final check model exists
                            _logger.info(f"DYNAMIC match: Query words '{remaining_words_for_dynamic_match.intersection(model_name_tokens)}' matched tokens in '{model_human_name_lower}' ({model_orm_name})")
                            relevant_orm_models.add(model_orm_name)

            except Exception as e:
                _logger.exception(f"Error during dynamic model name matching with ir.model: {e}")

        # --- Step 3: Check for Explicit Technical Model Mentions (ORM or SQL style) ---
        for word_or_phrase in query_words: # Use normalized query_words
            # Check for ORM style: 'sale.order', 'res.partner'
            if '.' in word_or_phrase and word_or_phrase in request.env:
                _logger.info(f"EXPLICIT ORM model mention: '{word_or_phrase}' found.")
                relevant_orm_models.add(word_or_phrase)
                continue # Prioritize direct match

            # Check for SQL style: 'sale_order', 'res_partner' (convert to ORM and check)
            if '_' in word_or_phrase and not '.' in word_or_phrase:
                potential_orm_name = word_or_phrase.replace('_', '.')
                if potential_orm_name in request.env:
                    _logger.info(f"EXPLICIT SQL table mention '{word_or_phrase}' matched to ORM model '{potential_orm_name}'.")
                    relevant_orm_models.add(potential_orm_name)

        # Final check for all identified models: Ensure they actually exist in env
        # This is mostly redundant if checks are done when adding, but good safeguard.
        final_models = {m for m in relevant_orm_models if m in request.env}
        if not final_models and not query_text.lower().strip().startswith("select"):
             # If no models found and it's not already a direct SQL query, add some common defaults
             _logger.warning(f"No specific models extracted for query '{query_text}'. Adding common defaults for context.")
             default_models_to_check = ['res.partner', 'sale.order', 'product.product', 'account.move']
             final_models.update(m for m in default_models_to_check if m in request.env)


        _logger.info(f"Final ORM models extracted for SQL schema context: {final_models}")
        return list(final_models)


    # --- _get_sql_schema_context_for_models (Essential SQL Schema Fetcher) ---
    def _get_sql_schema_context_for_models(self, model_names):
        schema_context = {}
        if not model_names: return schema_context
        sql_table_names = [name.replace('.', '_') for name in model_names]
        if not sql_table_names: return schema_context # Handle if no conversion happens
        placeholders = ', '.join(['%s'] * len(sql_table_names))
        cr = request.env.cr
        # Refined query for PG common types and ensuring public schema if not specified.
        sql_query = f"""
            SELECT
                t.table_name,
                c.column_name,
                COALESCE(NULLIF(c.domain_name, ''), c.udt_name) as column_type, -- Get user-defined type if available, else base udt
                c.is_nullable,
                c.column_default
            FROM
                information_schema.tables t
            JOIN
                information_schema.columns c ON t.table_name = c.table_name AND t.table_schema = c.table_schema
            WHERE
                t.table_schema = 'public' AND
                t.table_type = 'BASE TABLE' AND
                t.table_name IN ({placeholders})
            ORDER BY
                t.table_name, c.ordinal_position;
        """
        try:
            cr.execute(sql_query, tuple(sql_table_names))
            column_defs = cr.dictfetchall()
            for row in column_defs:
                table_name_sql = row['table_name']
                if table_name_sql not in schema_context:
                    schema_context[table_name_sql] = {
                        "_comment": f"Schema for SQL table {table_name_sql} (derived from Odoo models {model_names})",
                        "columns": {}
                    }
                schema_context[table_name_sql]["columns"][row['column_name']] = {
                    'sql_type': row['column_type'], # Use specific SQL type
                    'nullable': row['is_nullable'] == 'YES',
                    'default': row['column_default']
                }
            _logger.info(f"Fetched SQL schema for tables: {list(schema_context.keys())}")
        except Exception as e:
            _logger.exception(f"Error fetching SQL schema from information_schema for tables {sql_table_names}: {e}")
            return {}
        return schema_context
    
    def _execute_sql_query_read_only(self, sql_query):
        """ Executes a read-only SQL query and returns results. """
        # Basic validation (already somewhat done in AI prompt and checked after AI returns)
        if not sql_query.strip().upper().startswith("SELECT"):
            _logger.error(f"Attempt to execute non-SELECT query: {sql_query[:200]}")
            raise UserError("Execution Error: Only SELECT queries are allowed.")

        cr = request.env.cr
        data = []
        headers = []
        try:
            # IMPORTANT: For production, ensure this uses a DB user with ONLY SELECT permissions
            # This example relies on Odoo's current cursor, which might have broader rights
            # For testing, if cr.execute gives permission error with complex queries/functions, it's likely Odoo's standard user perms.
            # Re-enable if sudo() proves problematic with security or functions.
            # With sudo() it means Odoo's SUPERUSER is running it which could bypass row-level if any, not just SELECT-only perm.
            # This decision needs CAREFUL thought for security. For now, assume standard execution.
            # sql_query = sql_query.replace('%', '%%') # Escape percent signs for psycopg2 if not already handled. Risky auto-replace.

            cr.execute(sql_query) # Execute the raw SQL

            if cr.description: # If query returns rows (not all SELECTs do, e.g. SELECT 1)
                headers = [desc[0] for desc in cr.description] # Column names
                # Fetch all rows. For very large results, pagination/streaming might be needed in future.
                # dictfetchall might be memory intensive for huge results, but simpler.
                raw_rows = cr.dictfetchall()

                # Convert all row values to strings for consistent JSON transport
                # and to handle non-JSON serializable types like datetime, decimal
                for raw_row in raw_rows:
                    data.append({k: str(v) if v is not None else '' for k, v in raw_row.items()})

                _logger.info(f"SQL query executed. Fetched {len(data)} rows, {len(headers)} columns.")
            else:
                _logger.info(f"SQL query executed but returned no column description (e.g., SELECT without results, or pure value SELECT).")
                # Still signal success but with a message or specific data structure
                return {'status': 'executed_no_data', 'message': 'Query executed successfully but returned no tabular data.'}

            return {'status': 'executed_success', 'headers': headers, 'data': data}

        
        except Exception as e: # Broader catch for other unexpected issues during execution
            _logger.exception(f"Unexpected error executing SQL: \n{sql_query}\nError: {e}")
            return {'status': 'execution_error', 'db_error': "An unexpected error occurred during query execution."}


    def _get_corrected_sql_from_ai(self, original_nl_query, failed_sql, db_error_msg,
                                   sql_schema_context_str, odoo_version_str, user_api_key):
        _logger.info(f"Attempting AI correction for failed SQL. NLQ: {original_nl_query[:50]}, Error: {db_error_msg[:100]}")
        try:
            client = openai.OpenAI(api_key=user_api_key)
            # === System Prompt for SQL Correction ===
            system_prompt_correction = f"""You are an Odoo SQL Query Debugging Expert for Odoo {odoo_version_str}.
The user asked: "{original_nl_query}"
An attempt to generate SQL resulted in the following query:
```sql
{failed_sql}
When this SQL was executed, it produced the PostgreSQL error: "{db_error_msg}"
The SQL Schema Context provided was: {sql_schema_context_str}
Review the original query, the failed SQL, the error message, and the schema.
STRICTLY return a JSON object with the following structure:
{{
"status": "corrected" | "uncorrectable", // If you can correct it or not
"corrected_sql": "Your corrected SQL query string here (ONLY if status is 'corrected', else null or original failed SQL)",
"explanation": "A brief (1-2 sentence) technical explanation of the error and your correction, OR why it's uncorrectable. Be concise."
}}
Ensure the corrected_sql is a read-only SELECT statement using only provided schema. If uncorrectable, explain simply.
"""
            # No user prompt here, the system prompt contains all context
            completion = client.chat.completions.create(
            model="gpt-4-turbo-preview", # Needs to be powerful for debugging
            messages=[{"role": "system", "content": system_prompt_correction}],
            temperature=0.2,
            response_format={"type": "json_object"}, # Expect JSON for correction
            max_tokens=1000
            )
            correction_response_str = completion.choices[0].message.content.strip()
            _logger.info(f"AI Correction Response (raw): {correction_response_str}")
            correction_data = json.loads(correction_response_str)
            return correction_data # Expected: {'status': '...', 'corrected_sql': '...', 'explanation': '...'}
        except Exception as e:
            _logger.exception("Error during AI SQL correction attempt:")
            return {'status': 'correction_api_error', 'explanation': "Error contacting AI for correction."}


    # === ACTUAL OPENAI CALL LOGIC (Replaces the placeholder _call_openai_for_sql) ===
    def _generate_sql_with_ai(self, nl_query, sql_schema_context_str, odoo_version_str, user_api_key):
        _logger.info(f"Calling OpenAI for SQL generation. NL Query: {nl_query[:100]}...")
        # Do not log the full key or very long schema unless in deep debug
        # _logger.debug(f"SQL Schema Context for AI:\n{sql_schema_context_str}")
        # _logger.debug(f"Odoo Version for AI: {odoo_version_str}")

        try:
            # Initialize OpenAI client with the user's key for THIS call
            client = openai.OpenAI(api_key=user_api_key)

            # --- Construct the System Prompt for SQL Generation ---
            current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z") # Needs to be generated here
            system_prompt = f"""You are an Odoo SQL Query Generation Expert. Your goal is to translate a user's natural language query into a single, valid, read-only PostgreSQL SELECT query suitable for their Odoo {odoo_version_str} database.

STRICTLY ADHERE to the following:
1.  **Use Provided Schema ONLY:** Base your query EXCLUSIVELY on the provided SQL Schema Context (table names, column names, SQL data types). Do NOT invent tables or columns not present in this context. Table names in the schema are actual SQL table names (e.g., 'res_partner', 'sale_order').
2.  **SQL Names:** The schema uses correct SQL table and column names (e.g., `sale_order`, `amount_total`). Use these exact names in your SQL.
3.  **Read-Only SELECT:** Generate ONLY `SELECT` statements. Absolutely NO `UPDATE`, `DELETE`, `INSERT`, `DROP`, `TRUNCATE`, `ALTER`, or any data-modifying DML/DDL.
4.  **PostgreSQL Syntax:** Ensure the query is valid PostgreSQL syntax.
5.  **Odoo Version:** Consider Odoo version `{odoo_version_str}` for any version-specific SQL functions if relevant (though usually standard SQL is fine).
6.  **Date Context:** The current date and time is `{current_time_str}`. Use this for relative date calculations (e.g., 'last month', 'this week'). Format date literals as 'YYYY-MM-DD'.
7.  **Joins:** Infer relationships and construct necessary `JOIN` clauses based on standard Odoo conventions (e.g., `res_partner.id` = `sale_order.partner_id`, `_rel` tables for many2many if context suggests it and the _rel table schema is provided) and the schema provided. If joining, ensure an appropriate `ON` condition.
8.  **Output Format:** Respond with ONLY the raw SQL query string. NO explanations, NO markdown, NO introductory text, NO start with ```sql SELECT...```.  Just the SQL statement in string format directly starting with SELECT.
9.  **If Ambiguous/Impossible:** If the query is too vague to generate valid SQL based *only* on the provided schema, or requires operations beyond a simple SELECT, respond with a single line starting with "ERROR_UNABLE_TO_GENERATE:" followed by a very brief explanation (e.g., "ERROR_UNABLE_TO_GENERATE: Cannot determine join path between provided tables based on schema."). Do NOT attempt a broken query.

User Natural Language Query will follow, then the SQL Schema Context.
"""
            # --- User Prompt for SQL Generation ---
            user_prompt_content = f"""User Natural Language Query:
{nl_query}

SQL Schema Context (PostgreSQL - use these exact table and column names):
```json
{sql_schema_context_str}"""
            _logger.info(f"Sending request to OpenAI (model: gpt-4-turbo-preview)") # Or your preferred model
            # If prompts get very long, might need gpt-4-turbo
            completion = client.chat.completions.create(
                model="gpt-4-turbo-preview", # Or "gpt-3.5-turbo" for faster/cheaper on simpler tasks
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt_content}
                ],
                temperature=0.1,  # Low temperature for more deterministic SQL
                max_tokens=1000    # Max length of generated SQL
                # No response_format={"type": "json_object"} needed here as we expect raw SQL
            )

            generated_sql = completion.choices[0].message.content.strip()
            _logger.info(generated_sql)
            # Check for our custom error prefix
            if generated_sql.startswith("ERROR_UNABLE_TO_GENERATE:"):
                error_message = generated_sql.replace("ERROR_UNABLE_TO_GENERATE:", "").strip()
                _logger.warning(f"OpenAI indicated inability to generate SQL: {error_message}")
                return {'status': 'generation_failed', 'error_reason': error_message}
            else:
                # Basic check if it looks like SQL (starts with SELECT)
                if not generated_sql.upper().startswith("SELECT"):
                    _logger.warning(f"AI returned non-SELECT statement: {generated_sql[:100]}")
                    return {'status': 'generation_failed', 'error_reason': 'AI returned an invalid (non-SELECT) query structure.'}
                _logger.info(f"OpenAI generated SQL: \n{generated_sql}")
                return {'status': 'sql_generated', 'sql_query': generated_sql}

        except openai.APIConnectionError as e:
            _logger.error(f"OpenAI API Connection Error: {e}")
            return {'status': 'error', 'error_detail': "Failed to connect to OpenAI API. Please check network."}
        except openai.RateLimitError as e:
            _logger.error(f"OpenAI API Rate Limit Exceeded: {e}")
            return {'status': 'error', 'error_detail': "OpenAI API rate limit exceeded. Please try again later or check your OpenAI plan."}
        except openai.AuthenticationError as e:
            _logger.error(f"OpenAI API Authentication Error: {e}") # Usually bad API key
            return {'status': 'error', 'error_detail': "OpenAI API Key is invalid or expired. Please check configuration."}
        except openai.APIError as e: # Other OpenAI API errors
            _logger.error(f"OpenAI API Error: {e}")
            return {'status': 'error', 'error_detail': f"An error occurred with the OpenAI API: {e}"}
        except Exception as e:
            _logger.exception("Unexpected error calling OpenAI for SQL generation:")
            return {'status': 'error', 'error_detail': "An unexpected error occurred during AI processing."}


    @route('/ai_sql/generate_sql/', type='json', auth='user', methods=['POST']) # Ensure module name is in route
    def handle_sql_generation_request(self, nl_query, attempt=1, previous_sql=None, previous_error=None):
        if not nl_query:
            return {'error': 'No natural language query provided.'}
        _logger.info(f"SQL Gen Request: Received NL query: '{nl_query}'")

        config_params = request.env['ir.config_parameter'].sudo()
        user_openai_api_key = config_params.get_param('niyu_odoo_ai.user_openai_api_key', False)
        if not user_openai_api_key:
            return {'status': 'config_error', 'error': 'OpenAI API Key is not configured.'}

        odoo_version_str = f"{release.series} ({release.version})"
        orm_model_names = self._extract_relevant_models_for_sql(nl_query) # Keep placeholder for now
        sql_schema_context_dict = self._get_sql_schema_context_for_models(orm_model_names)
        sql_schema_context_str = json.dumps(sql_schema_context_dict, indent=2) if sql_schema_context_dict else "{}"
        if not sql_schema_context_dict and orm_model_names: # if keyword match but schema failed
            _logger.warning("No SQL schema context generated despite model identification. AI might struggle.")

        if attempt == 1:
            ai_gen_result = self._generate_sql_with_ai(nl_query, sql_schema_context_str, odoo_version_str, user_openai_api_key)
        elif attempt == 2 and previous_sql and previous_error:
            # This is a correction attempt
            correction_data = self._get_corrected_sql_from_ai(
                nl_query, previous_sql, previous_error,
                sql_schema_context_str, odoo_version_str, user_openai_api_key
            )
            if correction_data.get('status') == 'corrected' and correction_data.get('corrected_sql'):
                ai_gen_result = {'status': 'sql_generated', 'sql_query': correction_data['corrected_sql']}
            elif correction_data.get('status') == 'uncorrectable':
                ai_gen_result = {'status': 'generation_failed', 'error_reason': correction_data.get('explanation', "AI could not correct the query."), 'final_attempt': True}
            else: # API error during correction or bad format
                ai_gen_result = {'status': 'generation_failed', 'error_reason': correction_data.get('explanation', "AI correction process failed."), 'final_attempt': True}
        else: # Should not happen
            return {'status': 'internal_error', 'error': 'Invalid attempt sequence.'}



        # Call the actual AI function
        # ai_result = self._generate_sql_with_ai(nl_query, sql_schema_context_str, odoo_version_str, user_openai_api_key)
        # --- Handle AI Generation Result ---
        if ai_gen_result.get('status') == 'sql_generated':
            generated_sql = ai_gen_result['sql_query']
            # --- Execute SQL Query ---
            exec_result = self._execute_sql_query_read_only(generated_sql)

            if exec_result.get('status') == 'executed_success':
                return {
                    'status': 'success_executed',
                    'sql_query': generated_sql,
                    'headers': exec_result['headers'],
                    'data': exec_result['data'],
                    'nl_query': nl_query
                }
            elif exec_result.get('status') == 'executed_no_data':
                return {
                    'status': 'success_no_data',
                    'sql_query': generated_sql,
                    'message': exec_result['message'],
                    'nl_query': nl_query
                }
            elif exec_result.get('status') == 'execution_error':
                if attempt == 1: # First execution attempt failed, try to correct
                    _logger.info("SQL execution failed, attempting AI correction (Attempt #2).")
                    # Trigger a call to self, but now for attempt #2
                    # Frontend will need to re-call, or we can make this synchronous?
                    # For simplicity now, we let frontend show error & maybe user retries
                    # OR, better, send a specific status to frontend to auto-retry IF we build that
                    # Let's design it to go for a second attempt from here
                    return self.handle_sql_generation_request(
                        nl_query=nl_query,
                        attempt=2,
                        previous_sql=generated_sql,
                        previous_error=exec_result['db_error']
                    )
                else: # Attempt #2 execution also failed
                    return {
                        'status': 'execution_failed_after_correction',
                        'sql_query': generated_sql, # The (potentially corrected) SQL that still failed
                        'error': exec_result['db_error'],
                        'original_nl_query': nl_query,
                        'ai_explanation_if_any': ai_gen_result.get('explanation') # If correction provided explanation
                    }
        elif ai_gen_result.get('status') == 'generation_failed':
            return {
                'status': 'generation_failed',
                'error': ai_gen_result.get('error_reason', 'AI failed to generate/correct SQL.'),
                'sql_query': previous_sql if attempt == 2 else None, # Show failing SQL if correction attempt
                'original_error_if_any': previous_error if attempt == 2 else None,
                'nl_query': nl_query,
                'final_attempt': ai_gen_result.get('final_attempt', False)
            }
        else: # API errors from _generate_sql_with_ai (like 'config_error', 'api_error')
            return ai_gen_result # Pass through the original error structure

        
        
    # In AISQLGeneratorController
    # === Excel Export Endpoint ===
    @route('/ai_sql/export_sql_results/', type='http', auth='user', methods=['POST'], csrf=False)
    def export_sql_results(self, sql_query, filename="niyu_sql_export.xlsx", **kwargs):
        if not sql_query:
            return request.make_response("No SQL query provided for export.", status=400)

        _logger.info(f"Exporting results for SQL query: {sql_query[:200]}...")

        # Execute the SQL query again to get fresh data for export
        # We already validated it's a SELECT upstream (or should have)
        # Use a new cursor for this operation if it's a separate request potentially?
        # For now, current env cursor is fine for a single request.
        cr = request.env.cr

        # sql_query = sql_query.replace('%', '%%') # Potentially escape for raw SQL
        cr.execute(sql_query)
        if not cr.description:
            return request.make_response("Query executed but returned no data to export.", status=404)

        headers = [desc[0] for desc in cr.description]
        # Fetchall might be memory intensive for huge results. Consider alternatives for V2.
        data_rows = cr.fetchall() # Fetch as list of tuples/lists

        # --- Generate Excel ---
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet()

        # Write headers
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3'})
        for col_num, header in enumerate(headers):
            worksheet.write(0, col_num, header, header_format)

        # Write data
        for row_num, row_data in enumerate(data_rows, 1):
            for col_num, cell_data in enumerate(row_data):
                # Basic type handling for xlsxwriter, can be expanded
                # if isinstance(cell_data, (datetime, datetime.date)):
                #     date_format = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm:ss' if isinstance(cell_data, datetime) else 'yyyy-mm-dd'})
                #     worksheet.write_datetime(row_num, col_num, cell_data, date_format)
                # else:
                worksheet.write(row_num, col_num, cell_data) # Handles numbers, strings, booleans

        workbook.close()
        output.seek(0)

        return request.make_response(
            output,
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', content_disposition(filename.replace(' ', '_'))),
            ]
        )
