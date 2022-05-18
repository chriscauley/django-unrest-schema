import math

noop = lambda i: i

def paginate(items, per_page=10, process=noop, extra={}, query_dict={}):
    page = int(query_dict.get('page') or 1)
    per_page = int(query_dict.get('per_page') or 0) or per_page
    offset = (page - 1) * per_page
    total = len(items)
    return {
        'pages': math.ceil(total / per_page),
        'items': [process(i) for i in items[offset: offset + per_page]],
        'page': page,
        'total': len(items),
        'next_page': page + 1 if offset + per_page < total else None,
        'prev_page': page - 1 if page > 1 else None,
        **extra,
    }