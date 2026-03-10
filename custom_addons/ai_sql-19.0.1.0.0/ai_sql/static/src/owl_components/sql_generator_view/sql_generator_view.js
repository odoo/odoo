/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { download } from "@web/core/network/download"; // For Excel download

export class SQLGeneratorView extends Component {
    static template = "ai_sql.SQLGeneratorView";

    setup() {
        this.state = useState({
            nlQuery: "",
            currentNLQueryForExecution: "", // Store NLQ used for the current displayed results
            generatedSQL: "",
            isRetrying: false, // To indicate if an AI correction is in progress

            // For UI feedback during generation/execution
            isLoading: false,
            generationStatus: "", // 'sql_generated', 'generation_failed', 'api_error', 'config_error', 'internal_error', 'correction_attempted'
            generationMessage: "", // User-facing message

            // For SQL execution results
            resultsHeaders: [],
            resultsData: [],
            executionError: "",
            executionMessage: "", // For success messages like "no data returned"
            aiCorrectionExplanation: "", // Explanation from AI if correction fails

            // For export
            isExporting: false,
        });
        this.notification = useService("notification");
    }

    // --- SQL GENERATION LOGIC ---
    async onGenerateSQL() {
        if (!this.state.nlQuery.trim()) {
            this.notification.add("Please enter your question.", { type: "warning" });
            return;
        }
        // Reset states for a new query generation
        this._resetGenerationState();
        this._resetExecutionState();
        this.state.isLoading = false;
        this.state.currentNLQueryForExecution = this.state.nlQuery; // Store the query being processed

        await this._callGenerateSQLAPI(this.state.nlQuery);
        this.state.isLoading = false;
    }

    async _callGenerateSQLAPI(nlQuery, attempt = 1, previousSql = null, previousError = null) {
        this.state.isLoading = true; // Ensure loading is true for subsequent attempts too
        if (attempt > 1) {
            this.state.isRetrying = true;
            this.state.generationStatus = "correction_attempted";
            this.state.generationMessage = "Original SQL failed. Attempting AI correction...";
        }

        try {
            const rpcPayload = { nl_query: nlQuery };
            if (attempt > 1) {
                rpcPayload.attempt = attempt;
                rpcPayload.previous_sql = previousSql;
                rpcPayload.previous_error = previousError;
            }

            const result = await rpc("/ai_sql/generate_sql/", rpcPayload);
            console.log("RPC Result (Generate/Correct SQL):", result);

            this._handleGenerationResponse(result);

        } catch (err) {
            console.error("RPC Error (Generate/Correct SQL):", err);
            this.state.generationStatus = "internal_error";
            let errorMessage = "Error communicating with the server: ";
            if (err.message?.data?.message) errorMessage += err.message.data.message;
            else if (err.message) errorMessage += err.message;
            else errorMessage += "Unknown error";
            this.state.generationMessage = errorMessage;
            this.notification.add(this.state.generationMessage, { type: "danger" });
        } finally {
            if (!this.state.isRetrying || (this.state.isRetrying && this.state.generationStatus !== "correction_attempted")) {
                 // Only stop general loading if not waiting for retry or retry finished
                this.state.isLoading = false;
            }
            if (this.state.isRetrying && this.state.generationStatus !== "correction_attempted"){
                this.state.isRetrying = false; // Reset retry flag when final
            }
        }
    }

    _handleGenerationResponse(result) {
        // Reset relevant states before processing new response
        this.state.generatedSQL = result.sql_query || this.state.generatedSQL; // Keep last good SQL if correction is still in progress

        if (result.status === 'sql_generated' && result.sql_query) {
            this.state.generationStatus = "sql_generated";
            this.state.generationMessage = "SQL Generated! Executing query...";
            this.state.generatedSQL = result.sql_query;
            // Automatically execute if successfully generated
            this._executeSQL(result.sql_query);
        } else if (result.status === 'generation_failed') {
            this.state.generationStatus = "generation_failed";
            this.state.generationMessage = result.error || "AI failed to generate valid SQL.";
            if(result.final_attempt){
                this.state.generationMessage += " (Final Attempt)";
                 this.state.isRetrying = false; // Ensure retry ends
            }
            this.notification.add(this.state.generationMessage, { type: "danger" });
        } else if (['api_error', 'config_error', 'internal_error'].includes(result.status)) {
            this.state.generationStatus = result.status;
            this.state.generationMessage = result.error || `An unexpected ${result.status} occurred.`;
            this.notification.add(this.state.generationMessage, { type: "danger" });
        } else if (result.status === 'success_executed' || result.status === 'success_no_data' || result.status === 'execution_failed_after_correction') {
            // This path means a correction attempt successfully generated SQL and it was executed by backend.
            // The handle_sql_generation_request controller function was updated to make nested call to itself.
            // This structure simplifies JS slightly by letting controller handle recursive retry.
            this._handleExecutionResponse(result);
        } else {
            this.state.generationStatus = "internal_error";
            this.state.generationMessage = "Unexpected response format from server during SQL generation.";
            this.notification.add(this.state.generationMessage, { type: "danger" });
        }
    }

    async _executeSQL(sqlQueryToExecute) {
        // This method is called by _handleGenerationResponse if SQL is generated.
        // The actual SQL execution and potential AI correction loop now happens entirely
        // within the handle_sql_generation_request controller method.
        // The frontend only needs to interpret the final outcome passed back.
        // So, no direct RPC call for execution from JS is strictly needed with the new controller logic.
        // The `status: success_executed` etc. from the initial `/generate_sql` RPC indicates result.
        console.log("Interpreting execution result received from server...");
        // State changes for execution display are handled by _handleGenerationResponse or _handleExecutionResponse
        // We implicitly know execution was attempted if `generationStatus` was 'sql_generated'.
        // The controller's response (result) will now include execution details.
        // We simply need to make sure that this 'result' object is properly processed.
    }


    _handleExecutionResponse(result) { // Called from _handleGenerationResponse if status implies execution
        this.state.generatedSQL = result.sql_query || this.state.generatedSQL; // Update SQL if it was corrected

        if (result.status === 'success_executed') {
            this.state.resultsHeaders = result.headers || [];
            this.state.resultsData = result.data || [];
            this.state.executionError = "";
            this.state.executionMessage = `Query executed successfully. Found ${this.state.resultsData.length} rows.`;
            this.notification.add("Query executed!", { type: "success" });
        } else if (result.status === 'success_no_data') {
            this.state.resultsHeaders = [];
            this.state.resultsData = [];
            this.state.executionError = "";
            this.state.executionMessage = result.message || "Query executed successfully but returned no data.";
             this.notification.add(this.state.executionMessage, { type: "info" });
        } else if (result.status === 'execution_failed_after_correction' || result.status === 'execution_error_initial_for_retry') {
             // The latter 'execution_error_initial_for_retry' is theoretical for a pure JS retry
             // With the controller handling retry, we get 'execution_failed_after_correction'
            this.state.resultsHeaders = [];
            this.state.resultsData = [];
            this.state.executionError = result.error || "SQL query execution failed.";
            this.state.aiCorrectionExplanation = result.ai_explanation_if_any || "";
            this.notification.add("SQL Execution Failed.", { type: "danger" });
        }
        this.state.isRetrying = false; // Ensure retry flag is cleared after execution path
    }


    // --- UI HELPER METHODS ---
    async copySQLToClipboard() {
        // ... (no change needed, should work)
        if (this.state.generatedSQL) {
            try {
                await navigator.clipboard.writeText(this.state.generatedSQL);
                this.notification.add("SQL copied to clipboard!", { type: "info" });
            } catch (err) {
                this.notification.add("Failed to copy SQL.", { type: "warning" });
            }
        }
    }

    async onExportExcel() {
        if (!this.state.generatedSQL || this.state.resultsHeaders.length === 0) {
            this.notification.add("No data to export.", { type: "warning" });
            return;
        }
        this.state.isExporting = true;
        try {
            // The filename for the downloaded file
            // const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, "-");
            const filename = `niyu_${this.state.nlQuery}.xlsx`;
            // const rpcPayload = { sql_query: this.state.generatedSQL}; 
            // const result = await rpc("/ai_sql/export_sql_results/", rpcPayload);
            // console.log("RPC Result (Generate/Correct SQL):", result);
            // await download(result);
            await download({
                url: '/ai_sql/export_sql_results/',
                data: {
                    sql_query: this.state.generatedSQL, // Send the SQL that produced the current results
                    filename: filename
                },
            });
            // Notification of success isn't strictly necessary as browser handles download prompt.
        } catch (err) {
            console.error("Export Error:", err);
            let errorMessage = "Failed to export data: ";
            if (err.message?.data?.message) errorMessage += err.message.data.message;
            else if (err.message) errorMessage += err.message;
            else errorMessage += "Unknown server error";
            this.notification.add(errorMessage, { type: "danger" });
        } finally {
            this.state.isExporting = false;
        }
    }

    _resetGenerationState() {
        this.state.generatedSQL = "";
        this.state.generationStatus = "";
        this.state.generationMessage = "";
        this.state.isRetrying = false;
    }

    _resetExecutionState() {
        this.state.resultsHeaders = [];
        this.state.resultsData = [];
        this.state.executionError = "";
        this.state.executionMessage = "";
        this.state.aiCorrectionExplanation = "";
    }
}

registry.category("actions").add("ai_sql.SQLGeneratorView", SQLGeneratorView);