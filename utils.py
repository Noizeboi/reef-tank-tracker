def strip_unicode(text):
    return text.encode("latin-1", errors="ignore").decode("latin-1")




def suggest_maintenance(tank):
    suggestions = []