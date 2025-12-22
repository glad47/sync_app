# models/warehouse_config.py
from odoo import models, fields, api

class WarehouseTransferConfig(models.Model):
    _name = 'warehouse.transfer.config'
    _description = 'Warehouse Transfer Configuration'
    _rec_name = 'app_warehouse_id'

    app_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='App Warehouse',
        required=True,
        help='The warehouse used for App operations'
    )
    
    mapping_ids = fields.One2many(
        'warehouse.contact.mapping',
        'config_id',
        string='Warehouse Contact Mappings'
    )
    
    @api.model
    def get_app_warehouse(self):
        """Get the configured App warehouse"""
        config = self.search([], limit=1)
        return config.app_warehouse_id if config else None
    
    @api.model
    def get_contact_for_warehouse(self, warehouse_id):
        """Get contact_id for a given warehouse_id"""
        config = self.search([], limit=1)
        if not config:
            return None
        
        mapping = config.mapping_ids.filtered(lambda m: m.warehouse_id.id == warehouse_id)
        return mapping.contact_id.id if mapping else None
    
    @api.model
    def get_all_mappings(self):
        """Get all warehouse-contact mappings as a dictionary"""
        config = self.search([], limit=1)
        if not config:
            return {}
        
        return {
            mapping.warehouse_id.id: mapping.contact_id.id
            for mapping in config.mapping_ids
        }


class WarehouseContactMapping(models.Model):
    _name = 'warehouse.contact.mapping'
    _description = 'Warehouse Contact Mapping'
    _rec_name = 'warehouse_id'
    
    config_id = fields.Many2one(
        'warehouse.transfer.config',
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
        required=True,
        domain=[('customer_rank', '>', 0)]
    )
    
    _sql_constraints = [
        ('unique_warehouse', 'UNIQUE(config_id, warehouse_id)', 
         'Each warehouse can only have one mapping!')
    ]