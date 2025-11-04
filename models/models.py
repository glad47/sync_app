from odoo import models, fields, api,_
from odoo.exceptions import  UserError
import requests


def send_webhook(payload):
        url = 'https://p.qeu.app/api/odoo/webhook'
        headers = {
            'Content-Type': 'application/json',
            # Add authentication if needed:
            # 'Authorization': 'Bearer YOUR_API_KEY'
        }
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            if response.ok:
                print("Request succeeded!")
            else:
                print("Request failed:", response.reason)

            # Print response body (JSON or text)
            try:
                print("Response JSON:", response.json())  # If response is JSON
            except ValueError:
                print("Response Text:", response.text)    # If not JSON

        except requests.exceptions.RequestException as e:
            print(e)
            # _logger = self.env['ir.logging']
            # _logger.create({
            #     'name': 'Webhook Error',
            #     'type': 'server',
            #     'level': 'error',
            #     'message': str(e),
            #     'path': url,
            #     'func': '_send_webhook',
            #     'line': 'N/A',
            # })


class ProductTemplate(models.Model):
    _inherit = 'product.template'


    

    @api.model
    def create(self, vals):
        result = super().create(vals)
        if result.product_variant_ids:
            # call the api for it fpr syncronization
            data = result.read()[0]

            # Convert datetime fields to strings
            for key, value in data.items():
                if isinstance(value, (fields.Datetime, fields.Date)) or hasattr(value, 'isoformat'):
                    data[key] = value.isoformat() if value else None

            payload = {
                "operation": 0,
                "type": 0,
                "model": self._name,
                "ids": result.ids,
                "data": data
            }
            send_webhook(payload)
        return result

    def write(self, vals):
        result = super().write(vals)
        if self.product_variant_ids:
            # call the api for it
            # call the api for it fpr syncronization
            if result: 

                # call the api for it fpr syncronization
                data = vals

                # Convert datetime fields to strings
                for key, value in data.items():
                    if isinstance(value, (fields.Datetime, fields.Date)) or hasattr(value, 'isoformat'):
                        data[key] = value.isoformat() if value else None

                payload = {
                    "operation": 1,
                    "type": 0,
                    "model": self._name,
                    "ids": self.ids,
                    "data": data
                }
                send_webhook(payload)
        return result

    def unlink(self):
        product_variant_ids = self.product_variant_ids
        ids = []
        name = ''
        if product_variant_ids:
            ids = product_variant_ids.ids
            name = product_variant_ids._name
        result = super().unlink()
        
        if result: 

            payload = {
                "operation": 2,
                "type": 0,
                "model": self._name,
                "ids": self.ids,
                "data": self.ids
            }
            send_webhook(payload)
        return result


class Product(models.Model):
    _inherit = 'product.product'

    write_date = fields.Datetime(
        'Last Updated on',  index=True, help="Date on which the record was last updated.")
    
    

    @api.model
    def create(self, vals):
        result = super().create(vals)
        data = result.read()[0]

        # Convert datetime fields to strings
        for key, value in data.items():
            if isinstance(value, (fields.Datetime, fields.Date)) or hasattr(value, 'isoformat'):
                data[key] = value.isoformat() if value else None

        payload = {
            "operation": 0,
            "type": 1,
            "model": self._name,
            "ids": result.ids,
            "data": data
        }
        send_webhook(payload)
        return result

    def write(self, vals):
        result = super().write(vals)
        if result: 

            # call the api for it fpr syncronization
            data = vals

            # Convert datetime fields to strings
            for key, value in data.items():
                if isinstance(value, (fields.Datetime, fields.Date)) or hasattr(value, 'isoformat'):
                    data[key] = value.isoformat() if value else None

            payload = {
                "operation": 1,
                "type": 1,
                "model": self._name,
                "ids": self.ids,
                "data": data
            }
            send_webhook(payload)
        return result

    def unlink(self):
        # ids = self.ids
        result = super().unlink()
        if result: 

            payload = {
                "operation": 2,
                "type": 1,
                "model": self._name,
                "ids": self.ids,
                "data": self.ids
            }
            send_webhook(payload)
        return result


class LoyaltyProgram(models.Model):
    _inherit = 'loyalty.program'

    write_date = fields.Datetime(
        'Last Updated on',  index=True, help="Date on which the record was last updated.")

    @api.model
    def create(self, vals):
        result = super().create(vals)
        # call the api for it fpr syncronization
        data = result.read()[0]

        # Convert datetime fields to strings
        for key, value in data.items():
            if isinstance(value, (fields.Datetime, fields.Date)) or hasattr(value, 'isoformat'):
                data[key] = value.isoformat() if value else None

        payload = {
            "operation": 0,
            "type": 2,
            "model": self._name,
            "ids": result.ids,
            "data": data
        }
        send_webhook(payload)
        return result

    def write(self, vals):
        if 'active' in vals and not vals.get('active', False) or ('pos_ok' in vals and not vals.get('pos_ok')):
            if 'date_to' in vals and vals.get('date_to') and fields.Date.to_date(vals.get('date_to')) >= fields.Date.today():
                raise UserError(_('You can not Archive or remove from POS a program that is still valid'))
            elif 'date_to' in vals and not vals.get('date_to'):
                raise UserError(_('You can not Archive or remove from POS a program that is still valid'))
            elif not 'date_to' in vals and not self.date_to:
                raise UserError(_('You can not Archive or remove from POS a program that is still valid'))
            elif not 'date_to' in vals and self.date_to and self.date_to >= fields.Date.today():
                raise UserError(_('You can not Archive or remove from POS a program that is still valid'))
        result = super().write(vals)
   

        if result: 

            # call the api for it fpr syncronization
            data = vals

            # Convert datetime fields to strings
            for key, value in data.items():
                if isinstance(value, (fields.Datetime, fields.Date)) or hasattr(value, 'isoformat'):
                    data[key] = value.isoformat() if value else None

            payload = {
                "operation": 1,
                "type": 2,
                "model": self._name,
                "ids": self.ids,
                "data": data
            }
            send_webhook(payload)
        return result

    def unlink(self):
        ids = self.ids
        result = super().unlink()
        if result: 

            payload = {
                "operation": 2,
                "type": 2,
                "model": self._name,
                "ids": self.ids,
                "data": self.ids
            }
            send_webhook(payload)
        return result

class LoyaltyRule(models.Model):
    _inherit = 'loyalty.rule'

    write_date = fields.Datetime(
        'Last Updated on',  index=True, help="Date on which the record was last updated.")

    @api.model
    def create(self, vals):
        result = super().create(vals)
        data = result.read()[0]

        # Convert datetime fields to strings
        for key, value in data.items():
            if isinstance(value, (fields.Datetime, fields.Date)) or hasattr(value, 'isoformat'):
                data[key] = value.isoformat() if value else None

        payload = {
            "operation": 0,
            "type": 3,
            "model": self._name,
            "ids": result.ids,
            "data": data
        }
        send_webhook(payload)
        return result

    def write(self, vals):
        result = super().write(vals)
        if result: 

            # call the api for it fpr syncronization
            data = vals

            # Convert datetime fields to strings
            for key, value in data.items():
                if isinstance(value, (fields.Datetime, fields.Date)) or hasattr(value, 'isoformat'):
                    data[key] = value.isoformat() if value else None

            payload = {
                "operation": 1,
                "type": 3,
                "model": self._name,
                "ids": self.ids,
                "data": data
            }
            send_webhook(payload)
        return result

    def unlink(self):
        ids = self.ids
        result = super().unlink()
        if result: 

            payload = {
                "operation": 2,
                "type": 3,
                "model": self._name,
                "ids": self.ids,
                "data": self.ids
            }
            send_webhook(payload)
        return result


class LoyaltyReward(models.Model):
    _inherit = 'loyalty.reward'

    write_date = fields.Datetime(
        'Last Updated on',  index=True, help="Date on which the record was last updated.")

    @api.model
    def create(self, vals):
        result = super().create(vals)

        data = result.read()[0]

        # Convert datetime fields to strings
        for key, value in data.items():
            if isinstance(value, (fields.Datetime, fields.Date)) or hasattr(value, 'isoformat'):
                data[key] = value.isoformat() if value else None

        payload = {
            "operation": 0,
            "type": 4,
            "model": self._name,
            "ids": result.ids,
            "data": data
        }
        send_webhook(payload)
        return result

    def write(self, vals):
        result = super().write(vals)
        if result: 

            # call the api for it fpr syncronization
            data = vals

            # Convert datetime fields to strings
            for key, value in data.items():
                if isinstance(value, (fields.Datetime, fields.Date)) or hasattr(value, 'isoformat'):
                    data[key] = value.isoformat() if value else None

            payload = {
                "operation": 1,
                "type": 4,
                "model": self._name,
                "ids": self.ids,
                "data": data
            }
            send_webhook(payload)
        return result
    def unlink(self):
        result = super().unlink()
        if result: 

            payload = {
                "operation": 2,
                "type": 4,
                "model": self._name,
                "ids": self.ids,
                "data": self.ids
            }
            send_webhook(payload)
        return result
