# -*- coding: utf-8 -*-
# Copyright 2017-2018 Quartile Limited
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from collections import defaultdict
from datetime import datetime

from openerp.modules.registry import RegistryManager
from openerp.osv import osv
from openerp import SUPERUSER_ID
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.addons.account_financial_report_webkit.report\
    .common_partner_reports import CommonPartnersReportHeaderWebkit


class PartnerStatementReport(report_sxw.rml_parse,
                                   CommonPartnersReportHeaderWebkit):

    def __init__(self, cursor, uid, name, context):
        super(PartnerStatementReport, self).__init__(
            cursor, SUPERUSER_ID, name, context=context)
        self.pool = RegistryManager.get(self.cr.dbname)
        self.cursor = self.cr

        company = self.pool.get('res.users').browse(
            self.cr, uid, uid, context=context).company_id
        header_report_name = ' - '.join((_('PARTNER STATEMENT REPORT'),
                                        company.name,
                                        company.currency_id.name))

        footer_date_time = self.formatLang(
            str(datetime.today()), date_time=True)

        self.localcontext.update({
            'cr': cursor,
            'uid': uid,
            'report_name': _('Partner Statement Report'),
            'display_account_raw': self._get_display_account_raw,
            'filter_form': self._get_filter,
            'target_move': self._get_target_move,
            'initial_balance': self._get_initial_balance,
            'amount_currency': self._get_amount_currency,
            'display_partner_account': self._get_display_partner_account,
            'display_target_move': self._get_display_target_move,
            'additional_args': [
                ('--header-font-name', 'Helvetica'),
                ('--footer-font-name', 'Helvetica'),
                ('--header-font-size', '10'),
                ('--footer-font-size', '6'),
                ('--header-left', header_report_name),
                ('--header-spacing', '2'),
                ('--footer-left', footer_date_time),
                ('--footer-right',
                 ' '.join((_('Page'), '[page]', _('of'), '[topage]'))),
                ('--footer-line',),
            ],
        })

    def _get_initial_balance_mode(self, start_period):
        balance_mode = self.pool.get('ir.config_parameter').get_param(
            self.cr, SUPERUSER_ID, 'initial_balance_mode'
        )
        if balance_mode and balance_mode == 'opening_balance':
            opening_period_selected = self.get_included_opening_period(
                start_period)
            opening_move_lines = self.periods_contains_move_lines(
                opening_period_selected)
            if opening_move_lines:
                return 'opening_balance'
        return 'initial_balance'

    def set_context(self, objects, data, ids, report_type=None):
        """Populate a statement_lines attribute on each browse record"""
        new_ids = data['form']['chart_account_id']

        # account partner memoizer
        # Reading form
        main_filter = self._get_form_param('filter', data, default='filter_no')
        target_move = self._get_form_param('target_move', data, default='all')
        start_date = self._get_form_param('date_from', data)
        stop_date = self._get_form_param('date_to', data)
        start_period = self.get_start_period_br(data)
        stop_period = self.get_end_period_br(data)
        fiscalyear = self.get_fiscalyear_br(data)
        partner_ids = self._get_form_param('partner_ids', data)
        result_selection = self._get_form_param('result_selection', data)
        chart_account = self._get_chart_account_id_br(data)

        if main_filter == 'filter_no' and fiscalyear:
            start_period = self.get_first_fiscalyear_period(fiscalyear)
            stop_period = self.get_last_fiscalyear_period(fiscalyear)

        # Retrieving accounts
        filter_type = ('payable', 'receivable')
        if result_selection == 'customer':
            filter_type = ('receivable',)
        if result_selection == 'supplier':
            filter_type = ('payable',)

        accounts = self.get_all_accounts(new_ids, exclude_type=['view'],
                                         only_type=filter_type)

        if not accounts:
            raise osv.except_osv(_('Error'), _('No accounts to print.'))

        if main_filter == 'filter_date':
            start = start_date
            stop = stop_date
        else:
            start = start_period
            stop = stop_period

        # when the opening period is included in the selected range of periods
        # and the opening period contains move lines, we must not compute the
        # initial balance from previous periods but only display the move lines
        # of the opening period we identify them as:
        #  - 'initial_balance' means compute the sums of move lines from
        #    previous periods
        #  - 'opening_balance' means display the move lines of the opening
        #    period
        init_balance = main_filter in ('filter_no', 'filter_period')
        initial_balance_mode = init_balance and self._get_initial_balance_mode(
            start) or False

        initial_balance_lines = {}
        initial_deposit_lines = {}
        if initial_balance_mode:
            if initial_balance_mode  == 'initial_balance':
                initial_balance_lines = self._compute_partners_initial_balances(
                    accounts, start_period, partner_filter=partner_ids,
                    exclude_reconcile=False)
            elif initial_balance_mode == 'opening_balance':
                opening_period_selected = self.get_included_opening_period(
                    start_period)
                initial_balance_lines = self._compute_partners_initial_balances(
                    accounts, start_period, partner_filter=partner_ids,
                    force_period_ids=opening_period_selected,
                    exclude_reconcile=False)
            initial_deposit_lines = self._compute_partners_deposit(
                accounts, main_filter, start, partner_filter=partner_ids)

        statement_lines = self._compute_partner_statement_lines(
            accounts, main_filter, target_move, start, stop,
            partner_filter=partner_ids)
        objects = self.pool.get('account.account').browse(self.cursor,
                                                          self.uid,
                                                          accounts)
        end_deposit_lines = self._compute_partners_deposit(
                accounts, main_filter, stop, partner_filter=partner_ids)

        init_balance = {}
        init_deposit = {}
        end_deposit = {}
        statement_lines_dict = {}
        partners_order = {}
        for account in objects:
            statement_lines_dict[account.id] = statement_lines.get(account.id,
                                                                   {})
            init_balance[account.id] = initial_balance_lines.get(account.id,
                                                                 {})
            init_deposit[account.id] = initial_deposit_lines.get(account.id,
                                                                 {})
            end_deposit[account.id] = end_deposit_lines.get(account.id,
                                                                 {})
            # we have to compute partner order based on initial balance
            # and statement line as we may have partner with init bal
            # that are not in statement line and vice versa
            statement_lines_pids = statement_lines.get(account.id, {}).keys()
            if initial_balance_mode:
                non_null_init_balances = dict(
                    [(ib, amounts) for ib, amounts
                     in init_balance[account.id].iteritems()
                     if amounts['init_balance'] or
                     amounts['init_balance_currency']])
                init_bal_lines_pids = non_null_init_balances.keys()
            else:
                init_balance[account.id] = {}
                init_bal_lines_pids = []

            partners_order[account.id] = self._order_partners(
                statement_lines_pids, init_bal_lines_pids)

        self.localcontext.update({
            'fiscalyear': fiscalyear,
            'start_date': start_date,
            'stop_date': stop_date,
            'start_period': start_period,
            'stop_period': stop_period,
            'partner_ids': partner_ids,
            'chart_account': chart_account,
            'initial_balance_mode': initial_balance_mode,
            'init_balance': init_balance,
            'init_deposit': init_deposit,
            'end_deposit': end_deposit,
            'statement_lines': statement_lines_dict,
            'partners_order': partners_order
        })

        return super(PartnerStatementReport, self).set_context(
            objects, data, new_ids, report_type=report_type)

    def _compute_partner_statement_lines(self, accounts_ids, main_filter,
                                      target_move, start, stop,
                                      partner_filter=False):
        res = defaultdict(dict)

        for acc_id in accounts_ids:
            move_line_ids = self.get_partners_move_lines_ids(
                acc_id, main_filter, start, stop, target_move,
                exclude_reconcile=False, partner_filter=partner_filter)
            if not move_line_ids:
                continue
            for partner_id in move_line_ids:
                partner_line_ids = move_line_ids.get(partner_id, [])
                lines = self._get_move_line_datas(list(set(partner_line_ids)))
                res[acc_id][partner_id] = lines
        return res

    def _get_move_line_datas(self, move_line_ids,
                             order='rec_id, per.special DESC, l.date ASC, \
                             per.date_start ASC, m.name ASC'):
        if not move_line_ids:
            return []
        if not isinstance(move_line_ids, list):
            move_line_ids = [move_line_ids]
        sql = """
            SELECT l.id AS id,
                l.date AS ldate,
                l.currency_id,
                l.account_id,
                l.amount_currency,
                l.name AS lname,
                COALESCE(l.debit, 0.0) - COALESCE(l.credit, 0.0) AS balance,
                l.debit,
                l.credit,
                l.period_id AS lperiod_id,
                per.code as period_code,
                per.special AS peropen,
                l.partner_id AS lpartner_id,
                p.name AS partner_name,
                m.name AS move_name,
                COALESCE(partialrec.name, fullrec.name, '') AS rec_name,
                COALESCE(partialrec.id, fullrec.id, NULL) AS rec_id,
                m.id AS move_id,
                c.name AS currency_code,
                i.id AS invoice_id,
                i.type AS invoice_type,
                i.number AS invoice_number,
                l.date_maturity,
                i.supplier_invoice_number as supplier_invoice_number,
                i.origin as quotation_number,
                av.reference as payment_ref,
                av.amount as payment_amt,
                av.type as payment_type,
                av.currency_id_name as payment_curr,
                av.narration as int_note,
                l.reconcile_invoice as invoice_ref,
                l.reconcile_order as order_ref,
                l.reconcile_item as reconcile_item_ref,
                CASE WHEN l.reconcile_id IS NOT NULL THEN 'full'
                     WHEN l.reconcile_partial_id IS NOT NULL THEN 'partial'
                ELSE 'unreconcile'
                END AS reconcile_state,
                aa.type as account_type
            FROM account_move_line l
            JOIN account_move m on (l.move_id = m.id)
            LEFT JOIN res_currency c on (l.currency_id = c.id)
            LEFT JOIN account_move_reconcile partialrec
                on (l.reconcile_partial_id = partialrec.id)
            LEFT JOIN account_move_reconcile fullrec on (l.reconcile_id = fullrec.id)
            LEFT JOIN res_partner p on (l.partner_id = p.id)
            LEFT JOIN account_invoice i on (m.id = i.move_id)
            LEFT JOIN account_period per on (per.id = l.period_id)
            LEFT JOIN account_voucher av on (m.id = av.move_id)
            LEFT JOIN account_account aa ON (l.account_id = aa.id)
            JOIN account_journal j on (l.journal_id = j.id)
            WHERE
                l.id in %s
                AND ((l.debit + l.credit) <> 0)
        """
        sql += (" ORDER BY %s" % (order,))
        try:
            self.cursor.execute(sql, (tuple(move_line_ids),))
            res = self.cursor.dictfetchall()
        except Exception:
            self.cursor.rollback()
            raise
        return res or []

    def _compute_partners_deposit(self, account_ids, main_filter, date,
                                  partner_filter=None):
        search_params = ({
            'account_ids': tuple(account_ids),
        })
        sql_conditions = ""
        if main_filter == 'date':
            # Get the date constraints
            periods = self._get_opening_periods()
            if not periods:
                periods = (-1,)
            sql_conditions = """
                AND aml.period_id not in %(period_ids)s
                AND aml.date <= date((%(date_stop)s))
            """
            search_params.update({'period_ids': tuple(periods),
                                  'date_stop': date})
        elif main_filter in ('period', 'filter_no'):
            # Get the period constraints
            periods = self.pool.get('account.period').build_ctx_periods(
                self.cr, self.uid, date.id, date.id)
            if periods:
                sql_conditions = """
                    AND aml.period_id not in %(period_ids)s
                    AND aml.date <= date((%(date_stop)s))
                """
                search_params.update({'period_ids': tuple(periods),
                                      'date_stop': date.date_stop})
        sql = """
        SELECT
            Subquery.partner_id,
            Subquery.account_id,
            SUM(Subquery.balance) AS balance
        FROM
        (
        SELECT
            CASE WHEN aa.type = 'receivable' AND aml.reconcile_partial_id IS NULL THEN SUM(aml.credit)
                 WHEN aa.type = 'payable' AND aml.reconcile_partial_id IS NULL THEN SUM(aml.debit)
                 WHEN aa.type = 'receivable' AND aml.reconcile_partial_id IS NOT NULL AND SUM(aml.credit) > SUM(aml.debit) THEN SUM(aml.credit) - SUM(aml.debit)
                 WHEN aa.type = 'payable' AND aml.reconcile_partial_id IS NOT NULL AND SUM(aml.debit) > SUM(aml.credit) THEN SUM(aml.debit) - SUM(aml.credit)
            ELSE 0
            END AS balance,
            aml.reconcile_partial_id AS reconcile_partial_id,
            aml.partner_id AS partner_id,
            aa.id AS account_id
        FROM
            account_move_line aml
        JOIN account_account aa ON (aml.account_id = aa.id)
        JOIN account_move am ON (aml.move_id = am.id)
        LEFT JOIN account_voucher av ON (am.id = av.move_id)
        WHERE
            aml.reconcile_id IS NULL
            AND aml.state = 'valid'
            AND aml.partner_id IS NOT NULL
            AND (aa.type = 'receivable' OR aa.type = 'payable')
        """
        if partner_filter:
            sql += "AND aml.partner_id in %(partner_ids)s"
            search_params.update({'partner_ids': tuple(partner_filter)})
        sql += sql_conditions
        sql += """
            AND aml.account_id in %(account_ids)s
        GROUP BY aml.partner_id, aml.reconcile_partial_id, aa.id
        ORDER BY aml.partner_id
        ) AS Subquery
            GROUP BY Subquery.partner_id, Subquery.account_id
        """

        try:
            self.cursor.execute(sql, search_params)
            res = self.cursor.dictfetchall()
        except Exception:
            self.cursor.rollback()
            raise
        return self._tree_move_line_ids(res)
