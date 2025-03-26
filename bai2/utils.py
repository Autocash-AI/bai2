import datetime
import re

from .constants import TypeCodes, TypeCode, TypeCodeLevel, TypeCodeTransaction
from .exceptions import NotSupportedYetException


def parse_date(value):
    """
    YYMMDD/YYYMMDD Format.
    """
    # Try parsing with a 4-digit year first
    try:
        return datetime.datetime.strptime(value, "%Y%m%d").date()
    except ValueError:
        # If parsing fails, check for 2-digit year (only if string length is 6)
        if len(value) == 6:
            value = "20" + value  # Assuming the 2-digit year is in the 2000s
            return datetime.datetime.strptime(value, "%Y%m%d").date()
        else:
            # If the value is not in a valid format, return None
            return datetime.datetime.strptime(value, '%y%m%d').date()


def write_date(date):
    return date.strftime('%y%m%d')


def parse_time(value):
    clock_pattern = re.compile(r'\d\d:\d\d:\d\d')

    if clock_pattern.match(value):
        return parse_clock_time(value)
    else:
        return parse_military_time(value)


def parse_clock_time(value):
    return datetime.datetime.strptime(value, '%H:%M:%S').time()


def parse_military_time(value):
    """
    Military Format, 24 hours. 0001 through 2400.
    Times are stated in military format (0000 through 2400).
    0000 indicates the beginning of the day and 2400 indicates the end of the day
    for the date indicated.
    Some processors use 9999 to indicate the end of the day.
    Be prepared to recognize 9999 as end-of-day when receiving transmissions.
    """
    # 9999 indicates end of the day
    # 2400 indicates end of the day but 24:00 not allowed so
    # it's really 23:59
    if value == '9999' or value == '2400':
        return datetime.time.max
    return datetime.datetime.strptime(value, '%H%M').time()


def write_time(time, clock_format_for_intra_day=False):
    if clock_format_for_intra_day and time != datetime.time.max:
        return write_clock_time(time)
    else:
        return write_military_time(time)


def write_clock_time(time):
    date = datetime.datetime.now().replace(hour=time.hour, minute=time.minute, second=time.second)
    return datetime.datetime.strftime(date, '%H:%M:%S')


def write_military_time(time):
    if time == datetime.time.max:
        return '2400'
    else:
        date = datetime.datetime.now().replace(hour=time.hour, minute=time.minute)
        return datetime.datetime.strftime(date, '%H%M')


def parse_summary_type_code(value):
    try:
        type_code = TypeCodes.get(value, None)
        if type_code:
            return type_code
        elif (int(value)>=1 and int(value)<100):
            return TypeCode(value, None, TypeCodeLevel.status, 'Custom Status')
        elif (int(value)>=101 and int(value)<=399):
            return TypeCode(value, TypeCodeTransaction.credit, TypeCodeLevel.summary, 'Custom Credit Summary')
        elif (int(value)>=401 and int(value)<=699):
            return TypeCode(value, TypeCodeTransaction.debit, TypeCodeLevel.summary, 'Custom Debit Summary')
        elif (int(value)>=700 and int(value)<=799):
            return TypeCode(value, TypeCodeTransaction.misc, TypeCodeLevel.summary, 'Custom Loan Summary')
        elif (int(value)>=900 and int(value)<=999):  
            return TypeCode(value, TypeCodeTransaction.misc, TypeCodeLevel.summary, 'Custom Summary')
            
    except KeyError:
        raise NotSupportedYetException(f"Type code '{value}' is not supported yet")
    
def parse_detail_type_code(value):
    try:
        type_code = TypeCodes.get(value, None)
        if type_code:
            return type_code
        elif (int(value)>=1 and int(value)<100):
            return TypeCode(value, None, TypeCodeLevel.status, 'Custom Status')
        elif (int(value)>=101 and int(value)<=399):
            return TypeCode(value, TypeCodeTransaction.credit, TypeCodeLevel.detail, 'Custom Credit Transaction Detail')
        elif (int(value)>=401 and int(value)<=699):
            return TypeCode(value, TypeCodeTransaction.debit, TypeCodeLevel.detail, 'Custom Debit Transaction Detail')
        elif (int(value)>=700 and int(value)<=799):
            return TypeCode(value, TypeCodeTransaction.misc, TypeCodeLevel.detail, 'Custom Loan Detail')
        elif (int(value)>=900 and int(value)<=999):  
            return TypeCode(value, TypeCodeTransaction.misc, TypeCodeLevel.detail, 'Custom Detail')
            
    except KeyError:
        raise NotSupportedYetException(f"Type code '{value}' is not supported yet")


def convert_to_string(value):
    if value is None:
        return ''
    else:
        return str(value)
