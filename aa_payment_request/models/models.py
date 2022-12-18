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

    @api.depends('settlement_line.amount')
    def _amount_settlement(self):
        for o in self:
            o.update({
                'settlement_total': sum([l.amount for l in o.settlement_line])
            })

    @api.depends('settlement_total', 'amount_total', 'amount_aap')
    def _amount_diff(self):
        for o in self:
            o.update({
                'amount_diff': o.amount_aap - (o.settlement_total + o.amount_total)
            })

    # FIELD PAYMENT REQUEST
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
    
    # FIELD ADVANCE PAYMENT
    description = fields.Char('Description', required=True, readonly=True, states={'draft' : [('readonly', False)]}, track_visibility='onchange')
    reason = fields.Text('Reason', readonly=True, states={'draft' : [('readonly', False)]}, track_visibility='onchange')
    method = fields.Selection([('cash', 'Cash'), ('transfer', 'Transfer')], string='Method', default='cash', required=True, readonly=True, states={'draft' : [('readonly', False)]})
    account_number = fields.Char('Account Number', readonly=True, states={'draft': [('readonly', False)]}, help='No Rekening')
    account_name = fields.Char('Account Name',  readonly=True, states={'draft': [('readonly', False)]}, help='Nama Rekening')
    bank_name = fields.Char('Bank', readonly=True, states={'draft': [('readonly', False)]}, help='Nama Bank')

    # FIELD SETTLEMENT
    advance_payment_id = fields.Many2one('payment.request', 'AAP', readonly=True, states={'draft' : [('readonly', False)]}, domain=[('type', '=', 'aap'), ('state', '=', 'paid'), ('advance_payment_id', '=', False)], track_visibility='onchange')
    amount_aap = fields.Monetary('Amount', related='advance_payment_id.amount_total', track_visibility='onchange')
    settlement_line = fields.One2many('settlement.line', 'payment_request_id', 'Payment Lines', readonly=True, states={'draft' : [('readonly', False)]})
    settlement_total = fields.Monetary('Total', store=True, compute='_amount_settlement', track_visibility='onchange')
    amount_diff = fields.Monetary('Difference', store=True, compute='_amount_diff', track_visibility='onchange')

    count_journal = fields.Integer(compute='compute_journal', string='Journal Entries')
    account_move_line = fields.One2many('account.move', 'payment_request_id', 'Account Move Lines', readonly=True)
    
 
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
            if o.type == 'as' and o.amount_diff < 0 :
               raise UserError(("Field Difference tidak boleh minus (pengeluaran biaya lebih besar dari uang muka) ! ")) 
            return o.write({'state': 'confirm'})

    def payment_done(self):
        for o in self:
            if o.settlement_line:
                o.advance_payment_id.advance_payment_id = o.id
                obj_move_line = self.env['account.move.line']

                move_lines = []; total = 0
                for line in o.settlement_line:
                    total += line.amount
                    move_lines.append((0, 0, {
                        'name': line.name,
                        'partner_id': line.partner_id.id if line.partner_id else False,
                        'account_id': line.account_id.id,
                        'credit': 0,
                        'debit': line.amount,
                    }))

                move_line_id = obj_move_line.search([('payment_request_line_id', '=', self.advance_payment_id.payment_line.id), ('balance', '>', 0)])
                move_lines.append((0, 0, {   
                    'name': "Reverse of Cash Advance %s" % self.advance_payment_id.name,
                    'account_id': move_line_id.account_id.id,
                    'credit': total,
                    'debit': 0,
                })) 

                move_id = self.env['account.move'].create({
                    'payment_request_id': o.id,
                    'journal_id': self.env['account.journal'].search([('type', '=', 'general')], limit=1).id,
                    'date': fields.Date.today(),
                    'ref': o.name,
                    'move_type': 'entry',
                    'line_ids': move_lines,
                })
                move_id._post()

                if not o.payment_line:
                    return o.write({'state': 'paid'})

            return o.write({'state': 'done'})

    @api.depends('account_move_line.payment_request_id')
    def compute_journal(self):
        for o in self:
            o.count_journal = len(o.account_move_line) or 0

    def open_journal(self):
        account_move_ids = []
        for o in self:
            for x in o.account_move_line:
                account_move_ids.append(x.id)

        return {
            'name': _('Journal Entries'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', account_move_ids)],
        }


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
        

class SettlementLine(models.Model):
    _name = 'settlement.line'

    payment_request_id = fields.Many2one('payment.request', 'Payment Reference', required=True, ondelete='cascade')
    name = fields.Char('Description', required=True)
    amount = fields.Monetary('Amount', required=True, digits=dp.get_precision('Product Price'))
    currency_id = fields.Many2one(related='payment_request_id.currency_id', depends=['payment_request_id'], store=True, string='Currency')
    partner_id = fields.Many2one('res.partner', 'Vendor')
    account_id = fields.Many2one('account.account', 'Account', required=True)
    

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

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    payment_request_line_id = fields.Many2one(related='statement_line_id.payment_request_line_id', depends=['statement_line_id'], store=True, string='APR')

class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'

    def button_validate(self):
        for l in self.line_ids:
            if l.payment_request_line_id:
                for x in self.env['account.move'].search([('statement_line_id', '=', l.id)]):
                    x.payment_request_id = l.payment_request_line_id.payment_request_id.id
        return super(AccountBankStatement, self).button_validate()
        