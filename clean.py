import json
import logging
import re


def print_and_log(msg):
    print(msg)
    logging.debug(msg)


def remove_ner_noise(ent_list):
    """Removes suspected noise like 'PER-1337' from NER tags."""
    ent_list_new = []
    for e in ent_list:
        ent_list_new.append((e[0], e[1], re.sub(r"-[0-9]*$", "", e[2])))
    return ent_list_new


def fix_borders(ent_list, text):
    
    def fix_char_index(text, i, i_is_start):
        """
        Takes the start or end index of a substring and moves it to the next valid character. Plenty
        of data has their indices offset by a few positions, so this needs to be corrected.
        
        Since the potentially wrong character of a given index can be either an invalid character (
        space, punctuation, etc.) or a valid character, this algorithm searches for the nearest
        border of character pairs. A border is defined as a difference between character pairs in
        one being valid and the other not.
        
        There is also a small bias introduced depending on the index being the start or end of a
        substring. If the index is at the start, then the search goes first to the left and then to
        the right, and then increases the search radius by a step of 1 in both directions, again
        searching first to the left. If the index is at the end, this is reversed.
        
        Also an explicit exception rule is introduced at the end checking for periods. Since a lot
        of periods are used as abbreviations (e.g. "N.Ö.") and this algorithm here interprets
        periods as invalid characters, a check at the end would correct this if the period is not
        at the end of the whole string, which would indicate a sentence boundary.
        """
        
        def is_char(s):
            return re.compile(r'[\w\d]', re.U).match(s)
        
        def is_not_char(s):
            return not is_char(s)
        
        # The boundary detection benefits from artificial boundaries attached to the start and end
        # so that the edge case of substrings at the start or end don't need to be handled with
        # some dedicated logic. indices i and i_correct later on must be corrected by one step.
        text = " " + text + " "
        i += 1
        # Depending on the index being at the start or end, the boundary must be flipped accordingly
        if i_is_start:
            is_border = lambda a, b: is_not_char(a) and is_char(b)
            i_step = -1
        else:
            is_border = lambda a, b: is_char(a) and is_not_char(b)
            i_step = 1
        i_current = i
        found = False
        while not found:
            i_a = i_current- 1
            i_b = i_current
            if i_a >= 0 and i_b < len(text) and is_border(text[i_a], text[i_b]):
                i_corrected = i_b
                found = True
            else:
                i_current += i_step
                if i_step > 0:
                    i_step += 1
                else:
                    i_step -= 1
                i_step *= -1
        # dedicated logic for the edge case of abbreviations. If a given period is not a sentence
        # boundary, it is included.
        if text[i_corrected] == "." and not re.compile(r'^\. *$', re.U).match(text[i_corrected:]):
            i_corrected += 1
        return i_corrected - 1
    
    def fix_parenthesis(ent, text):
        """
        There are some cases, where both the original data, and the correct one from the functions
        before have lost a parenthesis (e.g. 'Bad) Ischl'). This function checks if a character next
        to the boundaries is a parenthesis, and if it is, then checks if a non-matched counter
        exists in the substring. If so, then it is added.
        """
        i_a = ent[0]
        i_b = ent[1]
        text_sub = text[i_a:i_b]
        ent_new = ent
        if i_a > 0:
            if text[i_a - 1] == "(" and text_sub.count(")") > text_sub.count("("):
                ent_new = [i_a - 1, i_b, ent[2]]
        if i_b < len(text) - 1:
            if text[i_b] == ")" and text_sub.count("(") > text_sub.count(")"):
                ent_new = [i_a, i_b + 1, ent[2]]
        return ent_new
    
    def fix_borders_main(ent_list, text):
        ent_list_new = []
        for ent in ent_list:
            ent_new = [
                fix_char_index(text, ent[0], True),
                fix_char_index(text, ent[1], False),
                ent[2]
            ]
            ent_new = fix_parenthesis(ent_new, text)
            ent_list_new.append(ent_new)
            if ent != ent_new:
                print_and_log(
                    f"replaced: {ent}, text: {text[ent[0]:ent[1]].__repr__()},"
                    f" with: {ent_new}, text: {text[ent_new[0]:ent_new[1]].__repr__()}"
                )
            else:
                print_and_log(f"nothing replaced: {ent}, {text[ent[0]:ent[1]].__repr__()}")
            assert not (
                text[ent_new[0]:ent_new[1]].startswith(" ")
                or text[ent_new[0]:ent_new[1]].endswith(" ")
            )
        return ent_list_new
    
    return fix_borders_main(ent_list, text)
    
def deduplicate(ent_list):
    ent_list = [tuple(e) for e in ent_list]
    ent_set = set(e for e in ent_list)
    ent_list_new = list(ent_set)
    ent_list_new.sort(key=lambda x: x[2])
    ent_list_new.sort(key=lambda x: x[1])
    ent_list_new.sort(key=lambda x: x[0])
    if ent_list != ent_list_new:
        print_and_log(f"deduplicated from: {ent_list}, to: {ent_list_new}")
    return ent_list_new
    

def main():
    
    # config and load uncleaned data
    logging.basicConfig(
        filename='/veld/output/clean.log',
        filemode='w',
        level=logging.DEBUG,
        format='%(message)s',
    )
    file_path_input = "/veld/input/data.json"
    file_path_cleaned = "/veld/output/apis_oebl__ner__cleaned.json"
    file_path_cleaned_simplified = "/veld/output/apis_oebl__ner__cleaned_simplified.json"
    print_and_log(f"##################### processing {file_path_input}")
    with open(file_path_input, "r") as f:
        gd_list = json.load(f)
        
    # cleaning
    gd_list_cleaned = []
    for gd in gd_list:
        text = gd["text_raw"]
        print_and_log(f"cleaning ner data on text: {text.__repr__()}")
        ent_list = gd["entities"]
        if ent_list != []:
            ent_list = fix_borders(ent_list, text)
            ent_list = deduplicate(ent_list)
            gd_list_cleaned.append({"text_raw": text, "entities": ent_list})
        else:
            print_and_log(f"dropping because of no entities being present")
    print_and_log(f"##################### persisting {file_path_cleaned}")
    with open(file_path_cleaned, "w") as f:
        json.dump(gd_list_cleaned, f, indent=2)
        
    # cleaning and simplifying
    gd_list_cleaned_simplified = []
    for gd in gd_list_cleaned:
        text = gd["text_raw"]
        ent_list = gd["entities"]
        ent_list = remove_ner_noise(ent_list)
        ent_list = deduplicate(ent_list)
        gd_list_cleaned_simplified.append({"text_raw": text, "entities": ent_list})
    print_and_log(f"##################### persisting {file_path_cleaned_simplified}")
    with open(file_path_cleaned_simplified, "w") as f:
        json.dump(gd_list_cleaned_simplified, f, indent=2)
    
    
if __name__ == "__main__":
    main()
