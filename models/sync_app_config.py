# models/sync_app_config.py
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SyncAppConfig(models.Model):
    _name = 'sync.app.config'
    _description = 'Sync App Configuration'
    _rec_name = 'name'

    name = fields.Char(
        string='Configuration Name',
        default='Main Configuration',
        required=True
    )
    
    active = fields.Boolean(default=True)
    
    # ============================================
    # USER CONFIGURATION
    # ============================================
    app_user_id = fields.Many2one(
        'res.users',
        string='App User',
        help='The user used for App/API operations'
    )
    
    # ============================================
    # WAREHOUSE CONFIGURATION
    # ============================================
    app_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='App Warehouse',
        help='The main warehouse used for App operations'
    )
    
    # ============================================
    # POS CONFIGURATION
    # ============================================
    app_pos_config_id = fields.Many2one(
        'pos.config',
        string='App POS Config',
        help='The POS configuration used for App orders'
    )
    
    # ============================================
    # PAYMENT CONFIGURATION
    # ============================================
    app_payment_method_id = fields.Many2one(
        'pos.payment.method',
        string='POS Payment Method',
        help='The payment method used for POS orders'
    )
    
    app_payment_journal_id = fields.Many2one(
        'account.journal',
        string='Sales Payment Journal',
        domain=[('type', 'in', ['bank', 'cash'])],
        help='The journal used for Sales order payments'
    )
    
    # ============================================
    # WEBHOOK CONFIGURATION
    # ============================================
    webhook_enabled = fields.Boolean(
        string='Webhooks Enabled',
        default=True,
        help='Enable or disable webhook notifications'
    )
    
    webhook_url = fields.Char(
        string='Webhook URL',
        help='The URL to send webhook notifications to'
    )
    
    webhook_timeout = fields.Integer(
        string='Timeout (seconds)',
        default=10,
        help='Timeout in seconds for webhook requests'
    )
    
    webhook_retry_delay = fields.Integer(
        string='Retry Delay (seconds)',
        default=60,
        help='Delay in seconds before retrying a failed webhook'
    )
    
    webhook_max_retries = fields.Integer(
        string='Max Retries',
        default=0,
        help='Maximum retry attempts (0 = unlimited)'
    )
    
    webhook_verify_ssl = fields.Boolean(
        string='Verify SSL',
        default=True,
        help='Verify SSL certificates'
    )
    
    webhook_auth_token = fields.Char(
        string='Auth Token',
        help='Optional Bearer token for authentication'
    )
    
    # ============================================
    # WAREHOUSE CONTACT MAPPINGS
    # ============================================
    mapping_ids = fields.One2many(
        'warehouse.contact.mapping',
        'config_id',
        string='Warehouse Contact Mappings'
    )
    

    # ============================================
    # SALES TEAM CONFIGURATION
    # ============================================
    app_sales_team_id = fields.Many2one(
        'crm.team',
        string='Sales Team',
        required=False,
        help='The sales team used for App operations'
    )
    
    # ============================================
    # CONSTRAINTS
    # ============================================
    @api.constrains('active')
    def _check_single_active(self):
        for record in self:
            if record.active:
                other_active = self.search([
                    ('id', '!=', record.id),
                    ('active', '=', True)
                ])
                if other_active:
                    raise ValidationError('Only one active configuration is allowed.')
    
    @api.constrains('webhook_timeout')
    def _check_webhook_timeout(self):
        for record in self:
            if record.webhook_timeout and record.webhook_timeout < 1:
                raise ValidationError('Webhook timeout must be at least 1 second')
    
    @api.constrains('webhook_retry_delay')
    def _check_webhook_retry_delay(self):
        for record in self:
            if record.webhook_retry_delay and record.webhook_retry_delay < 1:
                raise ValidationError('Retry delay must be at least 1 second')


class WarehouseContactMapping(models.Model):
    _name = 'warehouse.contact.mapping'
    _description = 'Warehouse Contact Mapping'
    _rec_name = 'warehouse_id'
    
    config_id = fields.Many2one(
        'sync.app.config',
        string='Configuration',
        required=True,
        ondelete='cascade'
    )
    
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        required=True
    )
    
    contact_id = fields.Many2one(
        'res.partner',
        string='Contact/Partner',
        required=True
    )
    
    notes = fields.Text(string='Notes')
    
    _sql_constraints = [
        ('unique_warehouse_per_config', 
         'UNIQUE(config_id, warehouse_id)', 
         'Each warehouse can only have one mapping!')
    ]