# Copyright 2019 Quartile Limited
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.addons.report_xlsx.report.report_xlsx import ReportXlsxAbstract
from io import BytesIO
import base64


class ReportXlsxAbstract(ReportXlsxAbstract):

    def __init__(self, pool, cr):
        super(ReportXlsxAbstract, self).__init__(pool, cr)

        # main sheet which will contains report
        self.sheet = None

        # columns of the report
        self.columns = None

        # row_pos must be incremented at each writing lines
        self.row_pos = None

        # Formats
        self.format_right = None
        self.format_left = None
        self.format_right_bold_italic = None
        self.format_bold = None
        self.format_header_left = None
        self.format_header_center = None
        self.format_header_right = None
        self.format_header_amount = None
        self.format_amount = None
        self.format_number = None  # added by QTL
        self.format_percent = None  # added by QTL
        self.format_percent_bold_italic = None
        self.format_wrap = None  # added by QTL
        self.format_emphasis = None  # added by QTL

    def get_workbook_options(self):
        return {'constant_memory': True}

    def generate_xlsx_report(self, workbook, data, objects):
        report = objects

        self.row_pos = 0

        self._define_formats(workbook)

        report_name = self._get_report_name(report)
        report_footer = self._get_report_footer()
        filters = self._get_report_filters(report)
        self.columns = self._get_report_columns(report)
        self.workbook = workbook
        self.sheet = workbook.add_worksheet(report_name[:31])

        self._set_column_width()

        self._write_report_title(report_name)

        self._write_filters(filters)

        self._generate_report_content(workbook, report)

        self._write_report_footer(report_footer)

    def _define_formats(self, workbook):
        """ Add cell formats to current workbook.
        Those formats can be used on all cell.

        Available formats are :
         * format_bold
         * format_right
         * format_right_bold_italic
         * format_header_left
         * format_header_center
         * format_header_right
         * format_header_amount
         * format_amount
         * format_number  # added by QTL
         * format_percent  # added by QTL
         * format_percent_bold_italic
         * format_wrap  # added by QTL
         * format_emphasis  # added by QTL
        """
        self.format_bold = workbook.add_format({'bold': True})
        self.format_right = workbook.add_format({'align': 'right'})
        self.format_left = workbook.add_format({'align': 'left'})
        self.format_right_bold_italic = workbook.add_format(
            {'align': 'right', 'bold': True, 'italic': True}
        )
        self.format_header_left = workbook.add_format(
            {'bold': True,
             'border': True,
             'bg_color': '#FFFFCC'})
        self.format_header_left.set_text_wrap()  # added by QTL
        self.format_header_center = workbook.add_format(
            {'bold': True,
             'align': 'center',
             'border': True,
             'bg_color': '#FFFFCC'})
        self.format_header_center.set_text_wrap()  # added by QTL
        self.format_header_right = workbook.add_format(
            {'bold': True,
             'align': 'right',
             'border': True,
             'bg_color': '#FFFFCC'})
        self.format_header_right.set_text_wrap()  # added by QTL
        self.format_header_amount = workbook.add_format(
            {'bold': True,
             'border': True,
             'bg_color': '#FFFFCC'})
        currency_id = self.env['res.company']._get_user_currency()
        self.format_header_amount.set_num_format(
            '#,##0.'+'0'*currency_id.decimal_places)
        self.format_amount = workbook.add_format()
        self.format_amount.set_num_format('#,##0.00')
        self.format_number = workbook.add_format()  # added by QTL
        self.format_number.set_num_format('#,##0')  # added by QTL
        self.format_percent = workbook.add_format()  # added by QTL
        self.format_percent.set_num_format('#,##0.00%')  # added by QTL
        self.format_percent_bold_italic = workbook.add_format(
            {'bold': True, 'italic': True}
        )
        self.format_percent_bold_italic.set_num_format('#,##0.00%')
        self.format_wrap = workbook.add_format()  # added by QTL
        self.format_wrap.set_text_wrap()  # added by QTL
        self.format_emphasis = workbook.add_format({'bold': True})  # QTL
        self.format_emphasis.set_font_color('red')  # QTL

    def _set_column_width(self):
        """Set width for all defined columns.
        Columns are defined with `_get_report_columns` method.
        """
        for position, column in self.columns.items():
            self.sheet.set_column(position, position, column['width'])

    def _write_report_title(self, title):
        """Write report title on current line using all defined columns width.
        Columns are defined with `_get_report_columns` method.
        """
        self.sheet.merge_range(
            self.row_pos, 0, self.row_pos, len(self.columns) - 1,
            title, self.format_bold
        )
        self.row_pos += 3

    def _write_report_footer(self, footer):
        """Write report footer .
        Columns are defined with `_get_report_columns` method.
        """
        if footer:
            self.row_pos += 1
            self.sheet.merge_range(
                self.row_pos, 0, self.row_pos, len(self.columns) - 1,
                footer, self.format_left
            )
            self.row_pos += 1

    def _write_filters(self, filters):
        """Write one line per filters on starting on current line.
        Columns number for filter name is defined
        with `_get_col_count_filter_name` method.
        Columns number for filter value is define
        with `_get_col_count_filter_value` method.
        """
        col_name = 1
        col_count_filter_name = self._get_col_count_filter_name()
        col_count_filter_value = self._get_col_count_filter_value()
        col_value = col_name + col_count_filter_name + 1
        for title, value in filters:
            self.sheet.merge_range(
                self.row_pos, col_name,
                self.row_pos, col_name + col_count_filter_name - 1,
                title, self.format_header_left)
            self.sheet.merge_range(
                self.row_pos, col_value,
                self.row_pos, col_value + col_count_filter_value - 1,
                value)
            self.row_pos += 1
        self.row_pos += 2

    def write_array_title(self, title):
        """Write array title on current line using all defined columns width.
        Columns are defined with `_get_report_columns` method.
        """
        self.sheet.merge_range(
            self.row_pos, 0, self.row_pos, len(self.columns) - 1,
            title, self.format_bold
        )
        self.row_pos += 1

    def write_array_header(self):
        """Write array header on current line using all defined columns name.
        Columns are defined with `_get_report_columns` method.
        """
        for col_pos, column in self.columns.items():
            self.sheet.write(self.row_pos, col_pos, column['header'],
                             self.format_header_center)
        self.row_pos += 1

    def write_line(self, line_object, height=False):  # QTL
        """Write a line on current line using all defined columns field name.
        Columns are defined with `_get_report_columns` method.
        """
        for col_pos, column in self.columns.items():
            # >>> added by QTL
            if height:
                self.sheet.set_row(self.row_pos, height)
            # <<< added by QTL
            value = getattr(line_object, column['field'])
            cell_type = column.get('type', 'string')
            if cell_type == 'string':
                self.sheet.write_string(  # QTL
                    self.row_pos, col_pos, value or '', self.format_wrap
                )
            elif cell_type == 'amount':
                self.sheet.write_number(
                    self.row_pos, col_pos, float(value), self.format_amount
                )
            # >>> added by QTL
            elif cell_type == 'number':
                self.sheet.write_number(
                    self.row_pos, col_pos, value, self.format_number
                )
            elif cell_type == 'image':
                if line_object.image_small:
                    image = BytesIO(base64.b64decode(line_object.image_small))
                    self.sheet.insert_image(
                        self.row_pos, col_pos, 'image', {'image_data': image}
                    )
            elif cell_type == 'percent':
                self.sheet.write_number(
                    self.row_pos, col_pos, value, self.format_percent
                )
            # <<< added by QTL
        self.row_pos += 1

    def _generate_report_content(self, workbook, report):
        pass

    def _get_report_complete_name(self, report, prefix):
        if report.company_id:
            suffix = ' - %s - %s' % (
                report.company_id.name, report.company_id.currency_id.name)
            return prefix + suffix
        return prefix

    def _get_report_name(self, report):
        """
            Allow to define the report name.
            Report name will be used as sheet name and as report title.

            :return: the report name
        """
        raise NotImplementedError()

    def _get_report_footer(self):
        """
            Allow to define the report footer.
            :return: the report footer
        """
        return False

    def _get_report_columns(self, report):
        """
            Allow to define the report columns
            which will be used to generate report.

            :return: the report columns as dict

            :Example:

            {
                0: {'header': 'Simple column',
                    'field': 'field_name_on_my_object',
                    'width': 11},
                1: {'header': 'Amount column',
                     'field': 'field_name_on_my_object',
                     'type': 'amount',
                     'width': 14},
            }
        """
        raise NotImplementedError()

    def _get_report_filters(self, report):
        """
            :return: the report filters as list

            :Example:

            [
                ['first_filter_name', 'first_filter_value'],
                ['second_filter_name', 'second_filter_value']
            ]
        """
        raise NotImplementedError()

    def _get_col_count_filter_name(self):
        """
            :return: the columns number used for filter names.
        """
        raise NotImplementedError()

    def _get_col_count_filter_value(self):
        """
            :return: the columns number used for filter values.
        """
        raise NotImplementedError()