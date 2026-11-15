import os
import re


# Load the included English dictionary from the project folder
# The dictionary is public word data (SCOWL)
def load_dictionary():
    current_folder = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_folder, 'english_words.txt')
    dictionary_words = set()

    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            word = line.strip().lower()

            if word:
                dictionary_words.add(word)

    return dictionary_words


# Extract English words while keeping contractions like "don't" together
def extract_words(plaintext):
    words = re.findall(r"[A-Za-z]+(?:['’][A-Za-z]+)*", plaintext)
    cleaned_words = []

    for word in words:
        cleaned_words.append(word.lower().replace('’', "'"))

    return cleaned_words


# Check the guessed plaintext against an English dictionary
# Short words are skipped by default because i found that they match the chance very easily and dilutes the results
def validate_words(plaintext, minimum_length=4, dictionary_words=None):
    if minimum_length < 1:
        raise ValueError('Minimum word length must be greater than zero.')

    if dictionary_words is None:
        dictionary_words = load_dictionary()

    words = extract_words(plaintext)
    checked_words = 0
    matched_words = 0
    skipped_words = 0
    word_counts = {}

    for word in words:
        if len(word) < minimum_length:
            skipped_words += 1
            continue

        checked_words += 1

        if word in dictionary_words:
            matched_words += 1

        if word not in word_counts:
            word_counts[word] = 0
        word_counts[word] += 1

    # Collect a row for each unique word and its number of appearances
    word_results = []
    valid_unique = 0
    invalid_unique = 0

    for word in word_counts:
        is_valid = word in dictionary_words

        if is_valid:
            valid_unique += 1
        else:
            invalid_unique += 1

        word_results.append({
            'Word': word,
            'Occurrences': word_counts[word],
            'In dictionary': 'Yes' if is_valid else 'No'
        })

    word_results.sort(key=lambda row: (-row['Occurrences'], row['Word']))

    match_percentage = 0.0
    if checked_words > 0:
        match_percentage = round(matched_words / checked_words * 100, 2)

    unique_percentage = 0.0
    if len(word_results) > 0:
        unique_percentage = round(valid_unique / len(word_results) * 100, 2)

    return {
        'total_words': len(words),
        'checked_words': checked_words,
        'matched_words': matched_words,
        'unmatched_words': checked_words - matched_words,
        'skipped_words': skipped_words,
        'match_percentage': match_percentage,
        'valid_unique': valid_unique,
        'invalid_unique': invalid_unique,
        'unique_percentage': unique_percentage,
        'word_results': word_results,
        'dictionary_size': len(dictionary_words)
    }
