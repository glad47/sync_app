from odoo import models, fields, http, api
from odoo.http import request, route
import hashlib
import json


class AuthUserToken(models.Model):
    _name = 'auth.user.token'
    _description = 'API User Token'

    name = fields.Char(required=True)
    password_hash = fields.Char(required=True)
    token = fields.Char(readonly=True)
    token_expiration = fields.Datetime(readonly=True)

    def set_password(self, raw_password):
        self.password_hash = hashlib.sha256(raw_password.encode()).hexdigest()

    def check_password(self, raw_password):
        return self.password_hash == hashlib.sha256(raw_password.encode()).hexdigest()

    @api.model
    def create(self, vals):
        if 'password_hash' in vals:
            raw_password = vals.pop('password_hash')
            vals['password_hash'] = hashlib.sha256(raw_password.encode()).hexdigest()
        return super().create(vals)
    
    def write(self, vals):
        if 'password_hash' in vals:
            raw_password = vals.pop('password_hash')
            vals['password_hash'] = hashlib.sha256(raw_password.encode()).hexdigest()
        return super().write(vals)



    

    
