from collections import OrderedDict

from .models import \
    Bai2File, Bai2FileHeader, Bai2FileTrailer, \
    Group, GroupHeader, GroupTrailer, \
    AccountIdentifier, AccountTrailer, Account, \
    TransactionDetail
from .utils import write_date, write_military_time, convert_to_string
from .constants import CONTINUATION_CODE
from .conf import settings


class BaseWriter(object):

    def __init__(self, obj):
        self.obj = obj

    def write(self):
        raise NotImplementedError()


class BaseSectionWriter(BaseWriter):
    model = None
    header_writer_class = None
    child_writer_class = None
    trailer_writer_class = None

    def write(self):
        header = self.header_writer_class(self.obj.header).write()
        trailer = self.trailer_writer_class(self.obj.trailer).write()

        children = []
        for child in self.obj.children:
            children.append(self.child_writer_class(child).write())

        return '\n'.join([header] + children + [trailer])


class BaseSingleWriter(BaseWriter):
    model = None
    trailing_slash = True

    def _write_field_from_config(self, field_config):
        if isinstance(field_config, str):
            field_config = (field_config, lambda x: x)

        field_name, writer = field_config
        field_value = getattr(self.obj, field_name, None)
        output = writer(field_value) if field_value is not None else None

        if isinstance(output, dict):
            return output
        else:
            return {field_name: convert_to_string(output)}

    def _write_fields_from_config(self, fields_config):
        fields = OrderedDict()
        for field_config in fields_config:
            fields.update(self._write_field_from_config(field_config))
        return fields

    def _check_for_continuation(self, record, fields, field_name):
        return (False, fields[field_name])

    def write(self):
        record = ''
        fields = self._write_fields_from_config(self.fields_config)

        record += self.model.code.value
        for field_name in fields:
            continuation, field_value = self._check_for_continuation(
                record, fields, field_name
            )
            if continuation:
                record += '/\n'
                record += CONTINUATION_CODE + ',' + field_value
            else:
                record += ',' + field_value

        # if final field is empty, delimit with ,/
        if field_value == '':
            record += ',/'
        # otherwise, delimit with / unless we don't
        elif self.trailing_slash:
            record += '/'
        return record


def expand_availability(availability):
    fields = OrderedDict()
    for field, value in availability:
        if field == 'date':
            value = write_date(value) if value else None
        elif field == 'time':
            value = write_military_time(value) if value else None
        fields[field] = convert_to_string(value)
    return fields


class TransactionDetailWriter(BaseSingleWriter):
    model = TransactionDetail
    trailing_slash = False

    fields_config = [
        ('type_code', lambda tc: tc.code),
        'amount',
        ('funds_type', lambda ft: ft.value),
        ('availability', expand_availability),
        'bank_reference',
        'customer_reference',
        'text'
    ]

    def _check_for_continuation(self, record, fields, field_name):
        continuation = False
        field_value = fields[field_name]
        if field_name == 'text' and self.obj.text:
            current_index = 0
            field_value = ''

            if settings.TEXT_ON_NEW_LINE:
                continuation = True
            else:
                remaining_line_length = (settings.LINE_LENGTH - len(record)) - 1
                if remaining_line_length > 0:
                    field_value = self.obj.text[:remaining_line_length]
                    current_index = remaining_line_length

            while current_index < len(self.obj.text):
                if current_index > 0:
                    field_value += '\n' + CONTINUATION_CODE + ','

                end_index = current_index + (settings.LINE_LENGTH-3)
                field_value += (
                    self.obj.text[current_index:end_index]
                )
                current_index = end_index

        return (continuation, field_value)


def expand_summary_items(summary_items):
    items = OrderedDict()

    for n, summary_item in enumerate(summary_items):
        for summary_field_config in AccountIdentifierWriter.summary_fields_config:
            if isinstance(summary_field_config, str):
                summary_field_config = (summary_field_config, lambda x: x)

            summary_field_name, writer = summary_field_config
            field_value = summary_item.get(summary_field_name, None)
            value = writer(field_value) if field_value is not None else None
            items['%s_%s' % (summary_field_name, n)] = convert_to_string(value)
    return items


class AccountIdentifierWriter(BaseSingleWriter):
    model = AccountIdentifier

    fields_config = [
        'customer_account_number',
        'currency',
        ('summary_items', expand_summary_items)
    ]

    summary_fields_config = [
        ('type_code', lambda tc: tc.code),
        'amount',
        'item_count',
        ('funds_type', lambda ft: ft.value)
    ]

    def _check_for_continuation(self, record, fields, field_name):
        line_length = len(record) % settings.LINE_LENGTH
        field_length = len(fields[field_name]) + 2
        if (line_length + field_length) >= settings.LINE_LENGTH:
            return (True, fields[field_name])
        else:
            return (False, fields[field_name])


class AccountTrailerWriter(BaseSingleWriter):
    model = AccountTrailer

    fields_config = [
        'account_control_total',
        'number_of_records'
    ]


class AccountWriter(BaseSectionWriter):
    model = Account
    header_writer_class = AccountIdentifierWriter
    trailer_writer_class = AccountTrailerWriter
    child_writer_class = TransactionDetailWriter


class GroupHeaderWriter(BaseSingleWriter):
    model = GroupHeader

    fields_config = [
        'ultimate_receiver_id',
        'originator_id',
        ('group_status', lambda gs: gs.value),
        ('as_of_date', write_date),
        ('as_of_time', write_military_time),
        'currency',
        ('as_of_date_modifier', lambda aodm: aodm.value)
    ]


class GroupTrailerWriter(BaseSingleWriter):
    model = GroupTrailer

    fields_config = [
        'group_control_total',
        'number_of_accounts',
        'number_of_records'
    ]


class GroupWriter(BaseSectionWriter):
    model = Group
    header_writer_class = GroupHeaderWriter
    trailer_writer_class = GroupTrailerWriter
    child_writer_class = AccountWriter


class Bai2FileHeaderWriter(BaseSingleWriter):
    model = Bai2FileHeader

    fields_config = (
        'sender_id',
        'receiver_id',
        ('creation_date', write_date),
        ('creation_time', write_military_time),
        'file_id',
        'physical_record_length',
        'block_size',
        'version_number'
    )


class Bai2FileTrailerWriter(BaseSingleWriter):
    model = Bai2FileTrailer

    fields_config = (
        'file_control_total',
        'number_of_groups',
        'number_of_records',
    )


class Bai2FileWriter(BaseSectionWriter):
    model = Bai2File
    header_writer_class = Bai2FileHeaderWriter
    trailer_writer_class = Bai2FileTrailerWriter
    child_writer_class = GroupWriter
