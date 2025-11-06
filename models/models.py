from odoo import models, fields, api,_
from odoo.exceptions import  UserError
import time
import requests
import threading


def webhook_worker(payload):
    url = 'https://p.qeu.app/api/odoo/webhook'
    headers = {
        'Content-Type': 'application/json',
        # 'Authorization': 'Bearer YOUR_API_KEY'
    }

    while True:
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()

            if response.ok:
                print("✅ Webhook succeeded!")
                try:
                    print("Response JSON:", response.json())
                except ValueError:
                    print("Response Text:", response.text)
                break  # Exit loop on success

            else:
                print("Webhook failed:", response.reason)

        except requests.exceptions.RequestException as e:
            print("Webhook error:", e)

        print("Retrying in 5 seconds...")
        time.sleep(60)  # Wait before retrying



def send_webhook(payload):
    thread = threading.Thread(target=webhook_worker, args=(payload,))
    thread.start()


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    @api.model
    def create(self, vals):
        result = super().create(vals)
        if result.product_variant_ids:
            # Define the fields you want to include
            fields_to_return = [
                'id', 'name', 'active', 'uom_id', 'barcode', 'categ_id',
                'taxes_id', 'route_ids', 'uom_po_id', 'list_price',
                'sale_delay', 'seller_ids', 'tax_string', 'create_date',
                'location_id', 'display_name', 'product_variant_ids'
            ]

            data = result.read(fields_to_return)[0]

            # Convert datetime fields to strings
            for key, value in data.items():
                if isinstance(value, (fields.Datetime, fields.Date)) or hasattr(value, 'isoformat'):
                    data[key] = value.isoformat() if value else None

            # Replace relational fields with full object data
            relational_fields = [
                'uom_id', 'categ_id', 'taxes_id', 'route_ids',
                'uom_po_id', 'seller_ids', 'product_variant_ids', 'location_id'
            ]

            for field in relational_fields:
                value = data.get(field)
            if isinstance(value, list) and value:  # many2many or one2many
                records = self.env[self.fields_get()[field]['relation']].browse([v[0] if isinstance(v, tuple) else v for v in value])
                data[field] = records.read()  # full object list
            elif isinstance(value, tuple) and value:  # many2one
                record = self.env[self.fields_get()[field]['relation']].browse(value[0])
                data[field] = record.read()[0] if record else None
            elif isinstance(value, int):  # fallback for many2one as int
                record = self.env[self.fields_get()[field]['relation']].browse(value)
                data[field] = record.read()[0] if record else None


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
        fields_to_return = [
                'id', 'code', 'name', 'active', 'uom_id', 'barcode', 'categ_id',
                'taxes_id', 'lst_price', 'route_ids', 'uom_po_id', 'list_price',
                'sale_delay', 'seller_ids', 'tax_string', 'create_date',
                'location_id', 'display_name', 'product_variant_ids'
            ]

        # Read only selected fields
        data = result.read(fields_to_return)[0]

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
        print("working with 1")
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
        # send_webhook(payload)
        return result

    def write(self, vals):
        print(" updating 1 ")
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
            # send_webhook(payload)
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
            # send_webhook(payload)
        return result
    

class LoyaltyRule(models.Model):
    _inherit = 'loyalty.rule'

    write_date = fields.Datetime(
        'Last Updated on',  index=True, help="Date on which the record was last updated.")

    @api.model
    def create(self, vals):
        print("working with 2")
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
        # send_webhook(payload)
        return result
    @api.model
    def write(self, vals):
        print(" updating 2 ")
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
            # send_webhook(payload)
        return result
    @api.model
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
            # send_webhook(payload)
        return result

# programs = env['loyalty.program'].search([])

# result = []
# for program in programs:
#     rules = env['loyalty.rule'].search([('program_id', '=', program.id)])
#     rewards = env['loyalty.reward'].search([('program_id', '=', program.id)])

#     for rule in rules:
#         eligible_relations = env['loyalty.rule.product.product.rel'].search([
#             ('loyalty_rule_id', '=', rule.id)
#         ])

#         for eligible_rel in eligible_relations:
#             eligible_product = eligible_rel.product_product_id
#             reward_product = rewards.filtered(lambda r: r.program_id.id == program.id).mapped('reward_product_id')

#             result.append({
#                 'program_id': program.id,
#                 'program_name': program.name.get('ar_001') or program.name.get('en_US') or '',
#                 'rule_id': rule.id,
#                 'rule_mode': rule.mode,
#                 'rule_active': rule.active,
#                 'discount_code': rule.code,
#                 'rule_min_qty': rule.minimum_qty,
#                 'rule_min_amount': rule.minimum_amount,

#                 'main_product_id': program.product_id.id,
#                 'main_product_name': program.product_id.name.get('ar_001') or program.product_id.name.get('en_US') or '',
#                 'main_product_barcode': program.product_id.barcode,
#                 'main_product_list_price': program.product_id.product_tmpl_id.list_price,

#                 'eligible_product_id': eligible_product.id,
#                 'eligible_product_name': eligible_product.name.get('ar_001') or eligible_product.name.get('en_US') or '',
#                 'eligible_product_barcode': eligible_product.barcode,
#                 'eligible_product_list_price': eligible_product.product_tmpl_id.list_price,

#                 'reward_product_id': reward_product[0].id if reward_product else False,
#                 'reward_product_name': reward_product[0].name.get('ar_001') or reward_product[0].name.get('en_US') if reward_product else '',
#                 'reward_product_barcode': reward_product[0].barcode if reward_product else '',
#                 'reward_product_list_price': reward_product[0].product_tmpl_id.list_price if reward_product else 0.0,

#                 'eligible_relation_id': eligible_rel.product_product_id.id,
#                 'rule_total_price': rule.total_price,
#                 'rule_after_discount': rule.after_dis,
#                 'rule_discount': rule.discount,
#             })


class LoyaltyReward(models.Model):
    _inherit = 'loyalty.reward'

    write_date = fields.Datetime(
        'Last Updated on',  index=True, help="Date on which the record was last updated.")
    
    def fetch_loyalty_data_by_program_local(self, program_id):
        query = """
            select * from loyalty_program;
        """
        self.env.cr.execute(query, (program_id,))
        return self.env.cr.dictfetchall()
    def fetch_loyalty_data_by_program(self, program_id):
        query = """

            SELECT
                lp.id AS program_id,
                COALESCE(lp.name->>'ar_001', lp.name->>'en_US', '') AS program_name,
                lr.id AS rule_id,
                lr.mode AS rule_mode,
                lr.active AS rule_active,
                lr.code AS discount_code,
                lr.minimum_qty AS rule_min_qty,
                lr.minimum_amount AS rule_min_amount,
                
                -- Main Product (from loyalty_program.product_id)
                pp_main.id AS main_product_id,
                COALESCE(pt_main.name->>'ar_001', pt_main.name->>'en_US', '') AS main_product_name,
                pp_main.barcode AS main_product_barcode,
                pt_main.list_price AS main_product_list_price,

                -- Eligible Product (from loyalty_rule_product_product_rel)
                pp_eligible.id AS eligible_product_id,
                COALESCE(pt_eligible.name->>'ar_001', pt_eligible.name->>'en_US', '') AS eligible_product_name,
                pp_eligible.barcode AS eligible_product_barcode,
                pt_eligible.list_price AS eligible_product_list_price,

                -- Reward Product (from loyalty_reward.reward_product_id)
                pp_reward.id AS reward_product_id,
                COALESCE(pt_reward.name->>'ar_001', pt_reward.name->>'en_US', '') AS reward_product_name,
                pp_reward.barcode AS reward_product_barcode,
                pt_reward.list_price AS reward_product_list_price,

                lrp.product_product_id AS eligible_relation_id,
                lr.total_price AS rule_total_price,
                lr.after_dis AS rule_after_discount,
                lr.discount AS rule_discount
            FROM loyalty_program lp
            LEFT JOIN loyalty_rule lr
                ON lr.program_id = lp.id
            LEFT JOIN product_product pp_main
                ON pp_main.id = lp.product_id
            LEFT JOIN product_template pt_main
                ON pt_main.id = pp_main.product_tmpl_id
                
            -- Eligible products
            LEFT JOIN loyalty_rule_product_product_rel lrp
                ON lrp.loyalty_rule_id = lr.id
            LEFT JOIN product_product pp_eligible
                ON pp_eligible.id = lrp.product_product_id
            LEFT JOIN product_template pt_eligible
                ON pt_eligible.id = pp_eligible.product_tmpl_id

            -- Reward products
            LEFT JOIN loyalty_reward lrw
                ON lrw.program_id = lp.id
            LEFT JOIN product_product pp_reward
                ON pp_reward.id = lrw.reward_product_id
            LEFT JOIN product_template pt_reward
                ON pt_reward.id = pp_reward.product_tmpl_id


            WHERE lr.program_id = %s

            ORDER BY lp.id, lr.id, pp_eligible.id, pp_reward.id;
        """
        self.env.cr.execute(query, (program_id,))
        return self.env.cr.dictfetchall()


    @api.model
    def create(self, vals):
        print("working with 3")
        result = super().create(vals)

        data = result.read()[0]

        # Convert datetime fields to strings
        for key, value in data.items():
            if isinstance(value, (fields.Datetime, fields.Date)) or hasattr(value, 'isoformat'):
                data[key] = value.isoformat() if value else None

        
        
        # # send_webhook(payload)
    
        print(result.program_id.id)
        res = self.fetch_loyalty_data_by_program_local(result.program_id.id)

        data_list = []

        for item in res:  # res is now a list of dicts
            data = {}
            for key, value in item.items():
                if isinstance(value, (fields.Datetime, fields.Date)) or hasattr(value, 'isoformat'):
                    data[key] = value.isoformat() if value else None
                else:
                    data[key] = value
            data_list.append(data)

        # print(res.read()[0])
        payload = {
                "operation": 0,
                "type": 2,
                "model": "loyalty.program",
                "ids": [],
                "data": data_list
            }
        send_webhook(payload)
        return result

    @api.model
    def write(self, vals):
        print(" updating 3 ")
        result = super().write(vals)
        if result:
            data_list = []
            for record in self:
                # Fetch all related reward data for this program
                res = self.fetch_loyalty_data_by_program_local(record.id)

                for item in res:  # res is a list of dicts
                    data = {}
                    for key, value in item.items():
                        if isinstance(value, (fields.Datetime, fields.Date)) or hasattr(value, 'isoformat'):
                            data[key] = value.isoformat() if value else None
                        else:
                            data[key] = value
                    data_list.append(data)

            payload = {
                "operation": 1,  # 1 for update
                "type": 2,
                "model": "loyalty.program",
                "ids": self.ids,
                "data": data_list
            }
            send_webhook(payload)
        return result
    @api.model
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
            # send_webhook(payload)
        return result
