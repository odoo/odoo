from odoo import http
from odoo.http import request
import json

class AssistantController(http.Controller):
    @http.route('/web/vendai/assistant/query', type='json', auth="user")
    def process_query(self, query, context=None):
        # Here we'll integrate with your LLM service
        try:
            # Get relevant context
            user_context = self._get_context(context)
            
            # Call LLM service (to be implemented)
            response = self._call_llm_service(query, user_context)
            
            return {
                'success': True,
                'response': response,
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_context(self, context):
        # Build context from current state
        env = request.env
        company = env.company
        
        base_context = {
            'user': request.env.user.name,
            'company': company.name,
            'current_view': context.get('view_type', 'form'),
            'model': context.get('model', False),
        }
        
        # Add model-specific context
        if context.get('active_model') and context.get('active_id'):
            record = request.env[context['active_model']].browse(context['active_id'])
            if record.exists():
                base_context['record'] = self._serialize_record(record)
        
        return base_context
    
    def _serialize_record(self, record):
        # Convert record to dict, handling common fields
        basic_fields = ['name', 'create_date', 'write_date']
        result = {
            'id': record.id,
            'model': record._name,
        }
        
        for field in basic_fields:
            if hasattr(record, field):
                result[field] = getattr(record, field)
                
        return result
