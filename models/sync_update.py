# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SyncUpdate(models.Model):
    _name = 'sync.update'
    _description = 'Sync Update Tracker'
    
    name = fields.Char(string='Name', default='Sync Tracker', required=True)
    last_product_sync = fields.Datetime(string='Last Product Sync')
    last_loyalty_sync = fields.Datetime(string='Last Loyalty Sync')
    last_receipt_sync = fields.Datetime(string='Last Receipt Sync')
    last_transfer_sync = fields.Datetime(string='Last Transfer Sync')
    last_delivery_sync =  fields.Datetime(string='Last Delivery Sync')
    
    @api.model
    def get_sync_record(self):
        """Get or create the single sync tracking record"""
        record = self.search([], limit=1)
        if not record:
            record = self.create({'name': 'Sync Tracker'})
        return record