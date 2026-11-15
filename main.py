import os
import sys
from attack_engine import read_ciphertext, attack_ciphertext_only
from frequency_analysis import letter_frequency, digram_frequency, trigram_frequency, index_of_coincidence
from dictionary_check import validate_words


# Return the most frequent letters or sequences as readable text
def top_sequences(counts):
    rows = []

    for sequence, count in counts.items():
        if count > 0:
            rows.append((sequence, count))

    rows.sort(key=lambda row: row[1], reverse=True)
    return ', '.join(sequence + ': ' + str(count) for sequence, count in rows[:10])


# Run the ciphertext-only attack from the command line
def main():
    current_folder = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(current_folder, 'cipher.txt')
    output_file = os.path.join(current_folder, 'recovered.txt')

    # Allow custom input and output paths without requiring a key
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]

    try:
        ciphertext = read_ciphertext(input_file)
        results = attack_ciphertext_only(ciphertext)
        result = results[0] # The candidate with the highest English score

        with open(output_file, 'w', encoding='utf-8') as file:
            file.write(result['plaintext'])

        print('Best plaintext candidate:')
        print(result['plaintext'])
        print('\nGuessed substitution table:', result['guessed_table'])
        print('English score:', round(result['score'], 4))
        print('Output saved to:', output_file)
        print('\nThis is a statistical guess, not guaranteed correct decryption.')

        # Analyze frequencies in the entire ciphertext, including adjacent blocks
        letter_counts = letter_frequency(result['blocks'])
        digram_counts = digram_frequency(result['blocks'], cross_blocks=True)
        trigram_counts = trigram_frequency(result['blocks'], cross_blocks=True)

        print('\nCiphertext frequency analysis:')
        print('Letters analyzed:', sum(letter_counts.values()))
        print('Index of coincidence:', round(index_of_coincidence(letter_counts), 4))
        print('Most common letters:', top_sequences(letter_counts))
        print('Most common digrams:', top_sequences(digram_counts))
        print('Most common trigrams:', top_sequences(trigram_counts))

        # Validate the recovered plaintext guess against the included word list
        validation = validate_words(result['plaintext'])
        print('\nDictionary validation (words with 4 or more letters):')
        print('Matched:', validation['matched_words'], 'out of', validation['checked_words'])
        print('Match rate:', str(validation['match_percentage']) + '%')

        if result['mono_letters'] < 100:
            print('Warning: This ciphertext is short, so key recovery may be unreliable.')

        print('\nBlock details:')
        for block in result['blocks']:
            print('Block:', block['number'] + 1)
            print('Type:', block['type'])
            print('Ciphertext:', ''.join(block['letters']))
            print('Plaintext guess:', block['plaintext'])

            if block['type'] == 'mono':
                print('Known rotation:', block['rotation'])
            else:
                print('Guessed lookahead:', block['lookahead'])
                print('Guessed Caesar shift:', block['shift'])
            print()

    except (OSError, UnicodeError, ValueError) as error:
        print('Error:', error)
        sys.exit(1)


if __name__ == '__main__':
    main()
