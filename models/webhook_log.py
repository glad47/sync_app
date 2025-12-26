# models/webhook_log.py
from odoo import models, fields, api

class WebhookLog(models.Model):
    _name = 'webhook.log'
    _description = 'Webhook Execution Log'
    _order = 'create_date desc'
    
    name = fields.Char(string='Reference', compute='_compute_name', store=True)
    url = fields.Char(string='Webhook URL', required=True)
    model = fields.Char(string='Model', required=True)
    operation = fields.Selection([
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete')
    ], string='Operation', required=True)
    record_ids = fields.Char(string='Record IDs')
    
    # Request details
    payload = fields.Text(string='Request Payload')
    headers = fields.Text(string='Request Headers')
    
    # Response details
    status = fields.Selection([
        ('pending', 'Pending'),
        ('sending', 'Sending'),
        ('success', 'Success'),
        ('error', 'Error'),
        ('retrying', 'Retrying')
    ], string='Status', default='pending', required=True)
    
    status_code = fields.Integer(string='HTTP Status Code')
    response_body = fields.Text(string='Response Body')
    error_message = fields.Text(string='Error Message')
    
    # Retry tracking
    retry_count = fields.Integer(string='Retry Count', default=0)
    max_retries = fields.Integer(string='Max Retries')
    next_retry_at = fields.Datetime(string='Next Retry At')
    
    # Timestamps
    sent_at = fields.Datetime(string='Sent At')
    completed_at = fields.Datetime(string='Completed At')
    
    # Duration
    duration_ms = fields.Integer(string='Duration (ms)', help='Time taken to receive response')
    
    @api.depends('model', 'operation', 'record_ids')
    def _compute_name(self):
        operation_names = {'create': 'Create', 'update': 'Update', 'delete': 'Delete'}
        for record in self:
            operation_name = operation_names.get(record.operation, 'Unknown')
            record.name = f"{record.model} - {operation_name} ({record.record_ids})"