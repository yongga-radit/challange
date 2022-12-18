from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError, RedirectWarning, ValidationError


class PaymentRequest(models.Model):
    _name = 'payment.request'
    _inherit = 'mail.thread'

    @api.depends('payment_line.amount')
    def _amount_all(self):
        for o in self:
            o.update({
                'amount_total': sum([l.amount for l in o.payment_line])
            })

    name = fields.Char('Reference', default='/', readonly=True)
    date = fields.Date('Date', required=True, default=fields.Date.context_today, readonly=True, states={'draft' : [('readonly', False)]}, track_visibility='onchange')
    user_id = fields.Many2one('res.users', string='Responsible', readonly=True, required=True, default=lambda self: self.env.user, copy=False)
    employee_id = fields.Many2one('hr.employee', string='Employee', readonly=True, states={'draft' : [('readonly', False)]}, track_visibility='onchange')
    department_id = fields.Many2one('hr.department', string='Department', related='employee_id.department_id', track_visibility='onchange')
    description = fields.Char('Description', required=True, readonly=True, states={'draft' : [('readonly', False)]}, track_visibility='onchange')
    type = fields.Selection([
        ('apr', 'Approval Payment Request'), 
        ('aap', 'Approval Advance Payment'), 
        ('as', 'Approval Settlement')
    ], string='Type', required=True, copy=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirm'),
        ('done', 'Approve'),
        ('paid', 'Paid'),
        ('cancel', 'Cancel'),
    ], string='Status', readonly=True, copy=False, default='draft', track_visibility='onchange')
    payment_line = fields.One2many('payment.request.line', 'payment_request_id', 'Payment Lines', readonly=True, states={'draft' : [('readonly', False)]})
    amount_total = fields.Monetary('Total', store=True, compute='_amount_all', track_visibility='onchange')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.user.company_id.currency_id)
    
    @api.model
    def create(self, vals):
        nama = '/'
        if vals['type'] == 'apr':
            nama = self.env['ir.sequence'].next_by_code('approval.payment.request')
        elif vals['type'] == 'aap':
            nama = self.env['ir.sequence'].next_by_code('approval.advance.payment')
        elif vals['type'] == 'as':
            nama = self.env['ir.sequence'].next_by_code('approval.settlements')
        vals['name'] = nama
        return super(PaymentRequest, self).create(vals)

    def unlink(self):
        for o in self:
            if o.state != 'draft':
                raise UserError(("Dokumen ini tidak bisa dihapus pada state %s !") % (o.state))
        return super(PaymentRequest, self).unlink()

    def payment_draft(self):
        for o in self:
            return o.write({'state': 'draft'})

    def payment_open(self):
        for o in self:
            return o.write({'state': 'confirm'})

    def payment_done(self):
        for o in self:
            return o.write({'state': 'done'})


class PaymentRequestLine(models.Model):
    _name = 'payment.request.line'

    payment_request_id = fields.Many2one('payment.request', 'Payment Reference', required=True, ondelete='cascade')
    name = fields.Char('Description', required=True)
    invoice_id = fields.Many2one('account.move', 'Vendor Bill', domain=[('state','=','posted'), ('move_type','=','in_invoice')])
    amount = fields.Monetary('Amount', required=True, digits=dp.get_precision('Product Price'))
    currency_id = fields.Many2one(related='payment_request_id.currency_id', depends=['payment_request_id'], store=True, string='Currency')
    state = fields.Selection([('open', 'Open'), ('paid', 'Paid')], string='Status', readonly=True, default='open')

    @api.onchange('invoice_id')
    def onchange_invoice_id(self):
        if self.invoice_id:
            self.amount = self.invoice_id.amount_total
            self.name = 'Payment Vendor Bill ' + self.invoice_id.partner_id.name

    def name_get(self):
        res = []
        for x in self:
            res.append((x.id, '[%s] %s # Rp. %d' % (x.payment_request_id.name, x.name, x.amount)))
        return res

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if operator not in ('ilike', 'like', '=', '=like', '=ilike'):
            return super(PaymentRequestLine, self).name_search(name, args, operator, limit)
        args = args or []
        domain = ['|', ('payment_request_id.name', operator, name), ('name', operator, name)]
        recs = self.search(domain + args, limit=limit)
        return recs.name_get()
        

class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    payment_request_line_id = fields.Many2one('payment.request.line', 'Payment Request Line', domain=[('state', '=', 'open'), ('payment_request_id.state','=','done')])

    @api.onchange('payment_request_line_id')
    def onchange_payment_request_line_id(self):
        if self.payment_request_line_id:
            n = -1
            if self.payment_request_line_id.payment_request_id.type == 'as':
                n = 1
            return {
                'value': {
                        'payment_ref': self.payment_request_line_id.name,
                        'ref': self.payment_request_line_id.invoice_id.name or False,
                        'amount': self.payment_request_line_id.amount * n,
                        'partner_id': self.payment_request_line_id.invoice_id.partner_id.id or False,
                }
            }

    def button_cancel_reconciliation(self):
        res = super(AccountBankStatementLine, self).button_cancel_reconciliation()

        for line in self:
            if line.payment_request_line_id:
                line.payment_request_line_id.state = 'open'
                line.payment_request_line_id.payment_request_id.state = 'approve'
        return res

    def process_reconciliation(self, counterpart_aml_dicts=None, payment_aml_rec=None, new_aml_dicts=None):
        res = super(AccountBankStatementLine, self).process_reconciliation(counterpart_aml_dicts, payment_aml_rec, new_aml_dicts)

        for line in self:
            if line.payment_request_line_id:
                line.payment_request_line_id.state = 'paid'
                if all([line.state == "paid" for line in line.payment_request_line_id.payment_request_id.payment_line]):
                    line.payment_request_line_id.payment_request_id.state = 'paid'
        return res
        
        
class AccountMove(models.Model):
    _inherit = 'account.move'

    payment_request_id = fields.Many2one('payment.request', 'Payment Request', readonly=True, copy=False)


class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'

    def check_confirm_bank(self):
        for l in self.line_ids:
            if l.payment_request_line_id.invoice_id:
                l.payment_request_line_id.invoice_id.payment_request_id = l.payment_request_line_id.payment_request_id.id

        super(AccountBankStatement, self).check_confirm_bank()
        return self.button_confirm_bank()