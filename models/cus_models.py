from odoo import models,http, fields, api,_
from odoo.exceptions import  UserError
import time
import requests
from odoo.http import request
import threading
import logging
import json
import random
import uuid
import datetime
import secrets
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


# the is the webhook that will ebe called to send the data to be sync with the application you get me, so we need to make sure that 
# the response is descriptive you get me 
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

        print("Retrying in 60 seconds...")
        time.sleep(60)  # Wait before retrying



def send_webhook(payload):
    thread = threading.Thread(target=webhook_worker, args=(payload,))
    thread.start()


def sanitize(obj):
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize(v) for v in obj]
    elif hasattr(obj, 'isoformat'):
        return obj.isoformat()
    return obj



class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    @api.model
    def create(self, vals):
        result = super().create(vals)
        if result.product_variant_ids:
            # Define the fields you want to include
            fields_to_return = [
                'id', 'name', 'uom_id', 'barcode', 'categ_id',
                'taxes_id', 'uom_po_id', 'list_price', 'sale_ok', 'purchase_ok', 'product_tag_ids',
                'sale_delay', 'seller_ids', 'tax_string', 'create_date', 'standard_price', 'volume_uom_name',
                'weight_uom_name', 'available_in_pos','description', 'attribute_line_ids', 'to_weight', 'pos_categ_id',
                'location_id', 'display_name', 'product_variant_ids', 'volume', 'weight', 'active'

            ]

            data = result.read(fields_to_return)[0]

            # Convert datetime fields to strings
            for key, value in data.items():
                if isinstance(value, (fields.Datetime, fields.Date)) or hasattr(value, 'isoformat'):
                    data[key] = value.isoformat() if value else None

            # Replace relational fields with full object data
            relational_fields = [
                'uom_id', 'categ_id', 'taxes_id', 'pos_categ_id',
                'uom_po_id', 'seller_ids', 'product_variant_ids', 
                'location_id', 'product_tag_ids', 'attribute_line_ids'
            ]

            for field in relational_fields:
                value = data.get(field)
                if isinstance(value, list) and value:  # many2many or one2many
                    records = self.env[self.fields_get()[field]['relation']].browse(
                        [v[0] if isinstance(v, tuple) else v for v in value]
                    )
                    data[field] = records.read()
                elif isinstance(value, tuple) and value:  # many2one
                    record = self.env[self.fields_get()[field]['relation']].browse(value[0])
                    data[field] = record.read()[0] if record else None
                elif isinstance(value, int):  # fallback for many2one as int
                    record = self.env[self.fields_get()[field]['relation']].browse(value)
                    data[field] = record.read()[0] if record else None

            # extract only  the name 
            # for field in relational_fields:
            #     value = data.get(field)
            #     relation = self.fields_get()[field]['relation']
 
            #     if field == 'product_variant_ids' and isinstance(value, list):
            #         # Extract only the IDs
            #         data[field] = [v[0] if isinstance(v, tuple) else v for v in value]
            #     elif field == 'attribute_line_ids' and isinstance(value, list) and value:  
            #         records = self.env[relation].browse([v[0] if isinstance(v, tuple) else v for v in value])
            #         data[field] = [r.display_name for r in records if hasattr(r, 'display_name')]
            #     elif isinstance(value, list) and value:  # many2many or one2many
            #         records = self.env[relation].browse([v[0] if isinstance(v, tuple) else v for v in value])
            #         data[field] = [r.name for r in records if hasattr(r, 'name')]
            #     elif isinstance(value, tuple) and value:  # many2one
            #         record = self.env[relation].browse(value[0])
            #         data[field] = record.name if record and hasattr(record, 'name') else None
            #     elif isinstance(value, int):  # fallback for many2one as int
            #         record = self.env[relation].browse(value)
            #         data[field] = record.name if record and hasattr(record, 'name') else None


            payload = {
                "operation": 0,
                "type": 0,
                "model": self._name,
                "ids": result.ids,
                "data": data
            }


            print("***************$$$$$$$$$**************")
            print(json.dumps(sanitize(payload["data"]), indent=4, ensure_ascii=False))
            
            # print(payload)


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
                'id','code', 'name', 'uom_id', 'barcode', 'categ_id',
                'taxes_id', 'uom_po_id','lst_price', 'list_price', 'sale_ok', 'purchase_ok', 'product_tag_ids',
                'sale_delay', 'seller_ids', 'tax_string', 'create_date', 'standard_price', 'volume_uom_name',
                'weight_uom_name', 'available_in_pos','description', 'attribute_line_ids', 'to_weight', 'pos_categ_id',
                'location_id', 'display_name', 'product_variant_ids', 'volume', 'weight','active',

            ]
       
        # Read only selected fields
        data = result.read(fields_to_return)[0]

        # Convert datetime fields to strings
        for key, value in data.items():
            if isinstance(value, (fields.Datetime, fields.Date)) or hasattr(value, 'isoformat'):
                data[key] = value.isoformat() if value else None

        # Replace relational fields with full object data
        relational_fields = [
            'uom_id', 'categ_id', 'taxes_id', 'pos_categ_id',
            'uom_po_id', 'seller_ids', 'product_variant_ids', 
            'location_id', 'product_tag_ids', 'attribute_line_ids'
        ]

        for field in relational_fields:
            value = data.get(field)
            if isinstance(value, list) and value:  # many2many or one2many
                records = self.env[self.fields_get()[field]['relation']].browse(
                    [v[0] if isinstance(v, tuple) else v for v in value]
                )
                data[field] = records.read()
            elif isinstance(value, tuple) and value:  # many2one
                record = self.env[self.fields_get()[field]['relation']].browse(value[0])
                data[field] = record.read()[0] if record else None
            elif isinstance(value, int):  # fallback for many2one as int
                record = self.env[self.fields_get()[field]['relation']].browse(value)
                data[field] = record.read()[0] if record else None        

        payload = {
            "operation": 0,
            "type": 1,
            "model": self._name,
            "ids": result.ids,
            "data": data
        }

        print("***************$$$$**************$$$$**************")
        print(json.dumps(sanitize(payload["data"]), indent=4, ensure_ascii=False))
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


# this is the LoyaltyProgram
class LoyaltyProgram(models.Model):
    _inherit = 'loyalty.program'

    write_date = fields.Datetime(
        'Last Updated on',  index=True, help="Date on which the record was last updated.")

    @api.model
    def create(self, vals):
        print("working with 1")
        result = super().create(vals)
        # call the api for it fpr syncronization
        # data = result.read()[0]

        # # Convert datetime fields to strings
        # for key, value in data.items():
        #     if isinstance(value, (fields.Datetime, fields.Date)) or hasattr(value, 'isoformat'):
        #         data[key] = value.isoformat() if value else None

        # payload = {
        #     "operation": 0,
        #     "type": 2,
        #     "model": self._name,
        #     "ids": result.ids,
        #     "data": data
        # }
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
        print("working with 2")
        result = super().create(vals)
        # data = result.read()[0]

        # # Convert datetime fields to strings
        # for key, value in data.items():
        #     if isinstance(value, (fields.Datetime, fields.Date)) or hasattr(value, 'isoformat'):
        #         data[key] = value.isoformat() if value else None

        # payload = {
        #     "operation": 0,
        #     "type": 3,
        #     "model": self._name,
        #     "ids": result.ids,
        #     "data": data
        # }
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
            send_webhook(payload)
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
            send_webhook(payload)
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
        res = self.fetch_loyalty_data_by_program(result.program_id.id)

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
            send_webhook(payload)
        return result




class PosSyncController(http.Controller):
    # we define a pos, user, stock for the App, also we make the payment method to be the Bank 
    # so that any order from the App shall its payment method be the BAnk 


    # get the user by the id named app 
    def get_user_id_by_name(self, username="App"):
        user = request.env['res.users'].sudo().search([('name', '=', username)], limit=1)
        if not user:
            return None  # or raise an exception if preferred
        return user.id



    # generate bank transfer statment 
    def generate_bank_transfer_statement(self, amount, method_name="Bank"):
        # Search for the payment method by name
        PaymentMethod = self.env['pos.payment.method'].sudo()
        method = PaymentMethod.search([('name', '=', method_name)], limit=1)

        if not method:
            raise ValueError(f"Payment method named '{method_name}' not found.")

        # Generate timestamp
        timestamp = fields.Datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Build statement_ids block
        statement_ids = [
            [0, 0, {
                "name": timestamp,
                "payment_method_id": method.id,
                "amount": amount,
                "payment_status": "",
                "ticket": "",
                "card_type": "",
                "cardholder_name": "",
                "transaction_id": ""
            }]
        ]

        return statement_ids


    def get_or_create_open_session_by_name(self, user_id, config_name="App"):
        PosConfig = request.env['pos.config'].sudo()
        PosSession = request.env['pos.session'].sudo()

        # Find the POS config by name
        config = PosConfig.search([('name', '=', config_name)], limit=1)
        if not config:
            raise ValueError(f"POS config named '{config_name}' not found.")

        # Search for an open session
        session = PosSession.search([
            ('config_id', '=', config.id),
            ('state', '=', 'opened')
        ], limit=1)

        if session:
            return session

        # Create and manually open a new session
        session = PosSession.create({
            'config_id': config.id,
            'user_id': user_id,
            'state': 'opened',
            'start_at': fields.Datetime.now(),
        })

        return session




    def generate_reward_code(self):
        return (str(random.random() + 1)[2:])

    
    def generate_temp_coupon_id(self):
        return -(int(time.time() * 1000) % 100000)
   
    # this is used to build the normal product line 
    def build_normal_product_line(self, product, qty, price_unit, price_subtotal, price_subtotal_incl, discount, tax_ids):
        return  [
            0,
            0, {
            "qty": qty,
            "price_unit": price_unit,
            "price_subtotal": price_subtotal,
            "price_subtotal_incl": price_subtotal_incl,
            "discount": discount,
            "product_id": product.id,
            "tax_ids": [[6, False, tax_ids]],
            "id": product.id,
            "pack_lot_ids": [],
            "description": product.description_sale or "",
            "full_product_name": product.name,
            "price_extra": 0,
            "price_manually_set": False,
            "price_automatically_set": False,
            "eWalletGiftCardProgramId": None
        }
        ]


    # this is used for the reward order line so as is expected
    def build_reward_product_line(self, product, qty, price_unit,price_subtotal, price_subtotal_incl, discount, tax_ids, reward_id, reward_product_id, points_cost):
        reward_identifier_code = self.generate_reward_code()
        coupon_id = self.generate_temp_coupon_id()

        reward_line = [
            0,
            0,
            {
                "qty": qty,
                "price_unit": price_unit,
                "price_subtotal": price_subtotal,
                "price_subtotal_incl": price_subtotal_incl,
                "discount": discount,
                "product_id": product.id,
                "tax_ids": [[6, False, tax_ids]],
                "id": product.id,
                "pack_lot_ids": [],
                "description": product.description_sale or "",
                "full_product_name": product.name,
                "price_extra": 0,
                "price_manually_set": False,
                "price_automatically_set": True,
                "is_reward_line": True,   # this is to check to is the reward line 
                "reward_id": reward_id, # this is the reward_id
                "reward_product_id": reward_product_id, # this is the reward_product_id
                "coupon_id": coupon_id, # this is the copoun id
                "reward_identifier_code": reward_identifier_code,
                "points_cost": points_cost,   # this is the points_cost
                "eWalletGiftCardProgramId": None
            }
        ]

         # Fetch applied rules from the reward program
        applied_rules = []
        if reward_id:
            reward = request.env['loyalty.reward'].sudo().browse(reward_id)
            if reward.exists() and reward.program_id:
                applied_rules = reward.program_id.rule_ids.ids

        # this is for the coupon
        coupon_point_change = {
            str(coupon_id): {
                "points": points_cost or 0,
                "program_id": reward.program_id.id,
                "coupon_id": coupon_id,
                "appliedRules": applied_rules
            }
        }


        return reward_line, coupon_point_change

   
    
    # this function used to build the order metadata
    def build_order_metadata(self, order_id, partner_id, session_id, user_id):
        return {
            "pos_session_id": session_id,
            "pricelist_id": 1,  # You can make this dynamic if needed
            "partner_id": partner_id,
            "user_id": user_id,
            "uid": order_id,
            "sequence_number": 4,  # You can auto-increment or generate this
            "creation_date": fields.Datetime.now().isoformat(),
            "fiscal_position_id": False,
            "server_id": False,
            "to_invoice": True,
            "to_ship": False,
            "is_tipped": False,
            "tip_amount": 0,
            "access_token": str(uuid.uuid4()),
            "disabledRewards": [],
            "codeActivatedProgramRules": [],
            "codeActivatedCoupons": []
        }
    
    # this is the to sync orders so that order from the application is send to the odoo and can be stored and tracked also include creating 
    # account.move 
    @http.route('/pos/sync_orders', type='json', auth='public', methods=['POST'])
    def sync_orders(self):
        
        token = request.httprequest.headers.get('Authorization')
        user = request.env['auth.user.token'].sudo().search([('token', '=', token)], limit=1)

        if not user or not user.token_expiration or user.token_expiration < datetime.utcnow():
            return {'error': 'Unauthorized or token expired'}, 401
        

        user_id = self.get_user_id_by_name("App")
        if not user_id:
            return {"status": "error", "message": "User named 'App' not found"}

        session = self.get_or_create_open_session_by_name(user_id, "App")
        session_id = session.id

        data = json.loads(request.httprequest.data)
        orders = data.get('orders', [])
        draft = data.get('draft', False)

        if not orders:
            return {'status': 'error', 'message': 'No orders provided'}

        all_prepared_orders = []

        for order in orders:
            order_id = order.get('id')
            order_data = order.get('data', {})

            order_name = order_data.get('name')
            amount_paid = order_data.get('amount_paid', 0)
            amount_total = order_data.get('amount_total', 0)
            amount_tax = order_data.get('amount_tax', 0)
            amount_return = order_data.get('amount_return', 0)

            customer_data = order_data.get('customer', {})
            phone = customer_data.get('phone')
            name = customer_data.get('name')
            vat = customer_data.get('vat')

            partner = request.env['res.partner'].sudo().search([
                ('phone', '=', phone),
                ('customer_rank', '>', 0)
            ], limit=1)

            if partner:
                updates = {}
                if name and partner.name != name:
                    updates['name'] = name
                if vat and partner.vat != vat:
                    updates['vat'] = vat
                if updates:
                    partner.write(updates)
            else:
                partner = request.env['res.partner'].sudo().create({
                    'name': name or phone,
                    'phone': phone,
                    'vat': vat,
                    'customer_rank': 1,
                })

            simplified_lines = order_data.get('order_lines', [])
            prepared_lines = []
            coupon_point_changes = {}

            for line in simplified_lines:
                qty = line.get('qty', 0)
                product_id = line.get('product_id', 0)
                price_unit = line.get('price_unit', 0)
                price_subtotal = line.get('price_subtotal', 0)

                price_subtotal_incl = line.get('price_subtotal_incl', 0)
                discount = line.get('discount', 0)

                

                product = request.env['product.product'].sudo().browse(product_id)
                if not product.exists():
                    return {
                        "status": "error",
                        "message": f"Product not found: ID {product_id}"
                    }

                tax_ids = product.taxes_id.ids if product.taxes_id else request.env['account.tax'].sudo().search([
                    ('type_tax_use', '=', 'sale'),
                    ('company_id', '=', request.env.company.id)
                ]).ids

                print("*********$$$$$$tax_ids$$$$$$**********")
                print(tax_ids)

                is_reward_line = line.get('is_reward_line', False)

                if is_reward_line:
                    reward_id = line.get('reward_id')
                    reward_product_id = line.get('reward_product_id')
                    points_cost = line.get('points_cost')

                    reward_line, coupon_change = self.build_reward_product_line(
                        
                        product, qty, price_unit, price_subtotal, price_subtotal_incl, discount, tax_ids,
                        reward_id, reward_product_id, points_cost
                    )

                    prepared_lines.append(reward_line)
                    coupon_point_changes.update(coupon_change)
                else:
                    normal_line = self.build_normal_product_line(product, qty, price_unit,price_subtotal, price_subtotal_incl, discount, tax_ids)
                    prepared_lines.append(normal_line)

            # Generate statement_ids using Bank method
            bank_method = request.env['pos.payment.method'].sudo().search([('name', '=', 'Bank')], limit=1)
            if not bank_method:
                return {"status": "error", "message": "Bank payment method not found"}

            statement_ids = [
                [0, 0, {
                    "name": fields.Datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "payment_method_id": bank_method.id,
                    "amount": amount_paid,
                    "payment_status": "",
                    "ticket": "",
                    "card_type": "",
                    "cardholder_name": "",
                    "transaction_id": ""
                }]
            ]

            metadata = self.build_order_metadata(
                order_id=order_id,
                partner_id=partner.id,
                session_id=session_id,
                user_id=user_id
            )

            all_prepared_orders.append({
                'id': order_id,
                'data': {
                    'name': order_name,
                    'customer_id': partner.id,
                    'lines': prepared_lines,
                    'couponPointChanges': coupon_point_changes,
                    'statement_ids': statement_ids,
                    'amount_paid': amount_paid,
                    'amount_total': amount_total,
                    'amount_tax': amount_tax,
                    'amount_return': amount_return,
                    **metadata 
                }
            })


        # return {
        #     "status": "success",
        #     "orders": all_prepared_orders,
        #     "draft": draft
        # }


      
        try:
            order_model = request.env['pos.order'].sudo()
            result = order_model.create_from_ui(all_prepared_orders, draft)
            return {
                'status': 'success',
                'processed_orders': result
            }
        except Exception as e:
            _logger.exception("Failed to sync PoS orders")
            return {
                'status': 'error',
                'message': str(e)
            }
    

    # this is the refunded_orders you can refund by normal or by all 
    @http.route('/pos/refund_orders', type='json', auth='public', methods=['POST'])
    def refund_orders(self):
        token = request.httprequest.headers.get('Authorization')
        user = request.env['auth.user.token'].sudo().search([('token', '=', token)], limit=1)

        if not user or not user.token_expiration or user.token_expiration < datetime.utcnow():
            return {'error': 'Unauthorized or token expired'}, 401
        
        user_id = self.get_user_id_by_name("App")
        if not user_id:
            return {"status": "error", "message": "User named 'App' not found"}

        session = self.get_or_create_open_session_by_name(user_id, "App")
        session_id = session.id

        data = json.loads(request.httprequest.data)
        orders = data.get('orders', [])
        draft = data.get('draft', False)

        if not orders:
            return {'status': 'error', 'message': 'No orders provided'}

        all_prepared_orders = []

        for order in orders:
            order_id = order.get('id')
            order_data = order.get('data', {})
            refunded_uid = order_data.get('refunded_uid')

            order_name = order_data.get('name')
            amount_paid = order_data.get('amount_paid', 0)
            amount_total = order_data.get('amount_total', 0)
            amount_tax = order_data.get('amount_tax', 0)
            amount_return = order_data.get('amount_return', 0)

            customer_data = order_data.get('customer', {})
            phone = customer_data.get('phone')
            name = customer_data.get('name')
            vat = customer_data.get('vat')

            partner = request.env['res.partner'].sudo().search([
                ('phone', '=', phone),
                ('customer_rank', '>', 0)
            ], limit=1)

            if partner:
                updates = {}
                if name and partner.name != name:
                    updates['name'] = name
                if vat and partner.vat != vat:
                    updates['vat'] = vat
                if updates:
                    partner.write(updates)
            else:
                partner = request.env['res.partner'].sudo().create({
                    'name': name or phone,
                    'phone': phone,
                    'vat': vat,
                    'customer_rank': 1,
                })

            simplified_lines = order_data.get('order_lines', [])
            prepared_lines = []
            coupon_point_changes = {}

            # Find original order lines for refund matching
            refunded_order = request.env['pos.order'].sudo().search([('pos_reference', '=', refunded_uid)], limit=1)
            refunded_lines = request.env['pos.order.line'].sudo().search([
                    ('order_id', '=', refunded_order.id)
                ])


            for line in simplified_lines:
                qty = line.get('qty')
                price_unit = line.get('price_unit')
                price_subtotal = line.get('price_subtotal', 0)

                price_subtotal_incl = line.get('price_subtotal_incl', 0)
                product_id = line.get('product_id')
                discount = line.get('discount', 0)

                product = request.env['product.product'].sudo().browse(product_id)
                if not product.exists():
                    return {
                        "status": "error",
                        "message": f"Product not found: ID {product_id}"
                    }

                tax_ids = product.taxes_id.ids if product.taxes_id else request.env['account.tax'].sudo().search([
                    ('type_tax_use', '=', 'sale'),
                    ('company_id', '=', request.env.company.id)
                ]).ids

                is_reward_line = line.get('is_reward_line', False)

                # Match refund line to original line
                refunded_line_id = False
                if qty < 0 and refunded_lines:
                    # Step 1: Find original lines for this product and price
                    candidate_lines = refunded_lines.filtered(
                        lambda l: l.product_id.id == product_id and l.qty > 0 and l.price_unit == price_unit
                    )

                    # Step 2: Loop through candidates to find one with refundable quantity
                    for original_line in candidate_lines:
                        # Step 3: Find all refund lines that reference this original line
                        refunded_lines_for_original = request.env['pos.order.line'].sudo().search([
                            ('refunded_orderline_id', '=', original_line.id),
                            ('qty', '<', 0)
                        ])

                        # Step 4: Calculate total refunded quantity
                        total_refunded_qty = sum(abs(refund.qty) for refund in refunded_lines_for_original)
                        remaining_qty = original_line.qty - total_refunded_qty

                        # Step 5: Validate refund quantity
                        if remaining_qty <= 0:
                            continue  # This line is fully refunded, try next one

                        if abs(qty) <= remaining_qty:
                            refunded_line_id = original_line.id
                            break
                        else:
                            return {
                                "status": "error",
                                "message": f"Refund quantity for product {product_id} exceeds remaining quantity ({remaining_qty})"
                            }

                    # Step 6: If no match found
                    if not refunded_line_id:
                        return {
                            "status": "error",
                            "message": f"Product {product_id} has already been fully refunded or no matching line found"
                        }



                if is_reward_line:
                    reward_id = line.get('reward_id')
                    reward_product_id = line.get('reward_product_id')
                    points_cost = line.get('points_cost')

                    reward_line, coupon_change = self.build_reward_product_line(
                        product, qty, price_unit,price_subtotal, price_subtotal_incl, discount, tax_ids,
                        reward_id, reward_product_id, points_cost
                    )
                    reward_line[2]['refunded_orderline_id'] = refunded_line_id
                    prepared_lines.append(reward_line)
                    coupon_point_changes.update(coupon_change)
                else:
                    normal_line = self.build_normal_product_line(product, qty, price_unit,price_subtotal, price_subtotal_incl, discount, tax_ids)
                    normal_line[2]['refunded_orderline_id'] = refunded_line_id
                    prepared_lines.append(normal_line)

            bank_method = request.env['pos.payment.method'].sudo().search([('name', '=', 'Bank')], limit=1)
            if not bank_method:
                return {"status": "error", "message": "Bank payment method not found"}

            statement_ids = [
                [0, 0, {
                    "name": fields.Datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "payment_method_id": bank_method.id,
                    "amount": amount_paid,
                    "payment_status": "",
                    "ticket": "",
                    "card_type": "",
                    "cardholder_name": "",
                    "transaction_id": ""
                }]
            ]

            metadata = self.build_order_metadata(
                order_id=order_id,
                partner_id=partner.id,
                session_id=session_id,
                user_id=user_id
            )

            all_prepared_orders.append({
                'id': order_id,
                'data': {
                    'name': order_name,
                    'customer_id': partner.id,
                    'lines': prepared_lines,
                    'couponPointChanges': coupon_point_changes,
                    'statement_ids': statement_ids,
                    'amount_paid': amount_paid,
                    'amount_total': amount_total,
                    'amount_tax': amount_tax,
                    'amount_return': amount_return,
                    **metadata 
                }
            })

        try:
            order_model = request.env['pos.order'].sudo()
            result = order_model.with_context(is_refund=True).create_from_ui(all_prepared_orders, draft)
            return {
                'status': 'success',
                'processed_orders': result
            }
        except Exception as e:
            _logger.exception("Failed to sync refund PoS orders")
            return {
                'status': 'error',
                'message': str(e)
            }
        

    # this is the api for the token so that it can be called to get token so can access the end point
    @http.route('/api/auth/token', type='json', auth='public', methods=['POST'])
    def get_token(self):
        params = json.loads(request.httprequest.data)
        username = params.get('username')
        password = params.get('password')

        user = request.env['auth.user.token'].sudo().search([('name', '=', username)], limit=1)
        if user and user.check_password(password):
            token = secrets.token_hex(32)
            expiration = datetime.utcnow() + timedelta(hours=24)
            user.sudo().write({'token': token, 'token_expiration': expiration})
            return {'token': token, 'expires_at': expiration.isoformat()}
        return {'error': 'Invalid credentials'}, 401    
            
        
