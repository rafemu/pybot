# יבוא החלקים
from templates_content_part1 import get_templates_part1
from templates_content_part2 import get_templates_part2
from templates_content_part3 import get_templates_part3

def get_templates():
    """
    פונקציה המחזירה את כל התבניות HTML
    """
    templates = {}
    
    # הוספת התבניות מהחלק הראשון (index.html ו-settings.html)
    templates.update(get_templates_part1())
    
    # לקיחת positions.html מהחלק השני (הגרסה המלאה והמתוקנת)
    templates['positions.html'] = get_templates_part2()['positions.html']
    
    # הוספת יתר התבניות מהחלק השלישי
    templates['watchlist.html'] = get_templates_part3()['watchlist.html']
    templates['logs.html'] = get_templates_part3()['logs.html']
    
    return templates