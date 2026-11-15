import os
import csv
import io
import streamlit as st

from attack_engine import attack_ciphertext_only, read_ciphertext
from cipher_utils import alphabet
from frequency_analysis import (
    letter_frequency, digram_frequency, trigram_frequency,
    frequency_percentages, index_of_coincidence, english_letter_percentages
)
from dictionary_check import load_dictionary, validate_words


# show recovered details for every Caesar and monoalphabetic block
def show_blocks(blocks):
    rows = []

    for block in blocks:
        row = {
            'Block': block['number'] + 1,
            'Type': block['type'],
            'Letter positions': str(block['start'] + 1) + '-' + str(block['end']),
            'Ciphertext': ''.join(block['letters']),
            'Recovered letters': block['plaintext'],
            'Rotations': block['rotation'],
            'Lookahead guess': block['lookahead'],
            'Caesar shift guess': block['shift']
        }
        rows.append(row)

    if rows:
        st.dataframe(rows, hide_index=True, use_container_width=True)
    else:
        st.info('No English letters were found in the ciphertext.')


# choose which blocks should be analyzed
def select_analysis_blocks(blocks):
    selection = st.selectbox('Analyze these blocks',
                             ['All blocks', 'Caesar blocks', 'Monoalphabetic blocks'])
    selected_blocks = []

    for block in blocks:
        if selection == 'All blocks':
            selected_blocks.append(block)
        elif selection == 'Caesar blocks' and block['type'] == 'caesar':
            selected_blocks.append(block)
        elif selection == 'Monoalphabetic blocks' and block['type'] == 'mono':
            selected_blocks.append(block)

    if selection == 'Monoalphabetic blocks':
        rotations = []

        for block in selected_blocks:
            if block['rotation'] not in rotations:
                rotations.append(block['rotation'])

        if rotations:
            options = ['All rotations'] + rotations
            selected_rotation = st.selectbox('Known substitution-table rotation', options)

            if selected_rotation != 'All rotations':
                filtered_blocks = []

                for block in selected_blocks:
                    if block['rotation'] == selected_rotation:
                        filtered_blocks.append(block)

                selected_blocks = filtered_blocks

    return selected_blocks, selection


# this is to turn the frequency counts into a list of rows for display and CSV output
def make_frequency_rows(counts):
    percentages = frequency_percentages(counts)
    rows = []

    for sequence, count in counts.items():
        rows.append({
            'Sequence': sequence,
            'Count': count,
            'Percentage': percentages[sequence]
        })

    rows.sort(key=lambda row: (-row['Count'], row['Sequence']))
    return rows


#single-letter frequencies + average English frequencies
def show_letter_frequencies(counts):
    st.write('**Single-letter frequency analysis**')
    total_letters = sum(counts.values())

    if total_letters == 0:
        st.info('There are no letters to analyze.')
        return

    percentages = frequency_percentages(counts)
    rows = []

    for char in alphabet:
        rows.append({
            'Letter': char,
            'Count': counts[char],
            'Observed %': percentages[char],
            'English reference %': english_letter_percentages[char]
        })

    rows.sort(key=lambda row: (-row['Count'], row['Letter']))
    st.bar_chart(rows, x='Letter', y=['Observed %', 'English reference %'])
    st.dataframe(rows, hide_index=True, use_container_width=True)


# most frequrent digrams and trigrams + their counts
def show_sequence_frequencies(title, counts, top_number):
    st.write('**' + title + '**')
    rows = make_frequency_rows(counts)

    if not rows:
        st.info('There arent enough letters for this analysis.')
        return

    st.bar_chart(rows[:top_number], x='Sequence', y='Count')
    st.dataframe(rows, hide_index=True, use_container_width=True)


# Generate CSV text for the complete frequency results
def make_frequency_csv(letter_counts, digram_counts, trigram_counts):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Type', 'Sequence', 'Count', 'Percentage'])

    for name, counts in [('Letter', letter_counts),
                         ('Digram', digram_counts),
                         ('Trigram', trigram_counts)]:
        rows = make_frequency_rows(counts)

        for row in rows:
            writer.writerow([name, row['Sequence'], row['Count'], row['Percentage']])

    return output.getvalue()


# Analyze the selected ciphertext or recovered plaintext letters
# Use the same frequency functions for both so their results are comparable
def show_frequency_analysis(blocks):
    st.subheader('Frequency analysis')
    source = st.radio('Text to analyze',
                      ['Ciphertext', 'Recovered plaintext guess'], horizontal=True)
    use_plaintext = source == 'Recovered plaintext guess'
    selected_blocks, selection = select_analysis_blocks(blocks)

    if not selected_blocks:
        st.info('No blocks match your selection.')
        return

    cross_blocks = selection == 'All blocks' # keep it for all blocks, checkbox wasnt working properlyu
    #top_number = st.slider('Number of digrams and trigrams shown in each graph', min_value=5, max_value=30, value=15, step=5)
    top_number = 20

    if selection == 'Monoalphabetic blocks': st.caption('The substitution table changes after every three monoalphabetic blocks. You can filter by rotation.')

    letter_counts = letter_frequency(selected_blocks, use_plaintext)
    digram_counts = digram_frequency(selected_blocks, use_plaintext, cross_blocks)
    trigram_counts = trigram_frequency(selected_blocks, use_plaintext, cross_blocks)
    total_letters = sum(letter_counts.values())
    ic_value = index_of_coincidence(letter_counts)

    columns = st.columns(4)
    columns[0].metric('Letters analyzed', total_letters)
    columns[1].metric('Digrams counted', sum(digram_counts.values()))
    columns[2].metric('Trigrams counted', sum(trigram_counts.values()))
    columns[3].metric('Index of coincidence', str(round(ic_value, 4)))

    show_letter_frequencies(letter_counts)
    show_sequence_frequencies('Digram frequency analysis', digram_counts, top_number)
    show_sequence_frequencies('Trigram frequency analysis', trigram_counts, top_number)

    csv_text = make_frequency_csv(letter_counts, digram_counts, trigram_counts)
    st.download_button('Download frequency analysis (CSV)', data=csv_text,file_name='frequency_analysis.csv', mime='text/csv')


# dictionary matches for the selected plaintext candidate
def show_dictionary_results(plaintext, dictionary_words):
    st.subheader('English dictionary validation')
    st.write('This checks words in the recovered plaintext **candidate** against the included English dictionary.')

    minimum_length = st.slider('Minimum word length to check',
                               min_value=2, max_value=8, value=4)
    results = validate_words(plaintext, minimum_length, dictionary_words)

    columns = st.columns(4)
    columns[0].metric('Words checked', results['checked_words'])
    columns[1].metric('Dictionary matches', results['matched_words'])
    columns[2].metric('Words not matched', results['unmatched_words'])
    columns[3].metric('Match rate', str(results['match_percentage']) + '%' if results['checked_words'] else 'N/A')

    st.caption(str(results['skipped_words']) + ' words were shorter than the selected minimum. They were not checked against the dictionary.')

    filter_option = st.selectbox('Show word matches', ['All checked words', 'Matched words only', 'Unmatched words only'])
    word_rows = []

    for row in results['word_results']:
        if filter_option == 'Matched words only' and row['In dictionary'] != 'Yes':
            continue
        if filter_option == 'Unmatched words only' and row['In dictionary'] != 'No':
            continue
        word_rows.append(row)

    if word_rows:
        st.dataframe(word_rows, hide_index=True, use_container_width=True)
    else:
        st.info('No words match the current filter.')

    st.caption('The match rate describes dictionary hits among the checked words. It is NOT the percentage of correctly recovered letters.')
    return results


# candidate keys summary table
def show_candidate_comparison(results, dictionary_words):
    rows = []

    for index, result in enumerate(results):
        validation = validate_words(result['plaintext'], 4, dictionary_words)
        match_rate = 'N/A'

        if validation['checked_words'] > 0:
            match_rate = str(validation['match_percentage']) + '%'

        rows.append({
            'Candidate': index + 1,
            'English score': round(result['score'], 4),
            'Dictionary match rate': match_rate,
            'Words checked': validation['checked_words']
        })

    st.dataframe(rows, hide_index=True, use_container_width=True)
    st.caption('Candidates are ranked by English n-gram score. Higher scores = more likely to be understandable English text.')


# explain what the analysis reveals and how to improve the cipher
def show_security_recommendations(result, dictionary_results):
    st.subheader('Attack explanation and security recommendations')

    st.write('**How the attack works:** The attacker knows the 6-letter Caesar / 8-letter substitution pattern and the rotation schedule, but NOT the initial substitution table. The program tests candidate tables, scores the resulting plaintext against general English letter patterns, and figures out Caesar shifts from the following guessed plaintext letters.')

    if result['mono_letters'] > 0:
        st.write('**What the dictionary adds:** ' + str(dictionary_results['matched_words']) +
                 ' of ' + str(dictionary_results['checked_words']) +
                 ' checked words appear in the dictionary. This helps evaluate whether the guessed plaintext is plausible and is readable, but common words can also appear by chance.')

    st.write('**Why the design is weak:** Repeating a predictable block pattern lets the attacker separate the two cipher methods. A substitution table reused across blocks preserves statistical relationships, and its rotation schedule is public. The Caesar shift is not a secret because it is dependent on the next plaintext letter.')

    st.write('**Recommended improvements:** For a real system, replace both the ciphers with authenticated encryption and use a strong random key and a fresh nonce for each message. Use an authenticated key-exchange protocol to for the keys.')


# Set up the main Streamlit interface
st.set_page_config(page_title='Ciphertext-Only Cryptanalysis', layout='wide')
st.title('Ciphertext-Only Cryptanalysis')
st.caption('CSCI Phase 2 | Public algorithm, unknown substitution key | Caesar + monoalphabetic cipher')

st.write('Upload encrypted text or paste it below.')

# Read the included sample without depending on the Windows working directory
if st.button('Load included sample ciphertext'):
    try:
        current_folder = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_folder, 'cipher.txt')
        st.session_state['pasted_ciphertext'] = read_ciphertext(file_path)
    except OSError as error:
        st.error('Unable to load sample: ' + str(error))

uploaded_file = st.file_uploader('Upload a ciphertext file', type=['txt'])
pasted_text = st.text_area('Or paste ciphertext here', height=110, key='pasted_ciphertext')

ciphertext = ''
if uploaded_file is not None:
    try:
        ciphertext = uploaded_file.getvalue().decode('utf-8-sig')
    except UnicodeDecodeError:
        st.error('The uploaded file must be a UTF-8 text file.')
        st.stop()

if pasted_text:
    ciphertext = pasted_text # Pasted text takes priority over an uploaded file

st.subheader('Attack settings')
restarts = st.slider('Number of key-search attempts', min_value=2, max_value=20, value=12, step=2)
steps = st.slider('Guesses per attempt', min_value=500, max_value=5000, value=3000, step=500)
st.caption('More attempts take longer but can improve the result.')

# Save the attack results when interacting with charts or word filters
if 'results' not in st.session_state:
    st.session_state['results'] = None
if 'attack_input' not in st.session_state:
    st.session_state['attack_input'] = None

if st.button('Attack ciphertext', type='primary'):
    if not ciphertext:
        st.error('Upload ciphertext, paste some text or load the sample first.')
    else:
        try:
            with st.spinner('Testing our substitution-key guesses against common English patterns...'):
                results = attack_ciphertext_only(ciphertext, restarts, steps)
            st.session_state['results'] = results
            st.session_state['attack_input'] = (ciphertext, restarts, steps)
        except (OSError, UnicodeError, ValueError) as error:
            st.error('Unable to analyze ciphertext: ' + str(error))

results = st.session_state['results']

if results is not None:
    if st.session_state['attack_input'] != (ciphertext, restarts, steps):
        st.info('Your ciphertext or settings changed!')
    else:
        st.subheader('Candidate plaintext results')
        st.warning('These are statistical guesses, not guaranteed to be correct. The original plaintext may never be revealed to the attacker.')

        if results[0]['mono_letters'] < 100:
            st.warning('There are fewer than 100 letters. The key recovery may be unreliable.')

        try:
            dictionary_words = load_dictionary()
        except OSError as error:
            st.error('Unable to load the included English dictionary: ' + str(error))
            st.stop()

        show_candidate_comparison(results, dictionary_words)

        if len(results) > 1:
            candidate_number = st.selectbox('Select a candidate key',
                                            list(range(1, len(results) + 1)))
        else:
            candidate_number = 1

        result = results[candidate_number - 1]
        st.write('**Guessed substitution table:**', result['guessed_table'] or 'Not recovered (no monoalphabetic blocks)')
        st.write('**English n-gram score:**', round(result['score'], 4))
        st.caption('A higher English score is better among the candidates. That does not mean the best candidate is correct but it is more likely to be understandable English text than the others.')

        st.text_area('Recovered plaintext candidate', result['plaintext'], height=170, disabled=True)
        st.download_button('Download recovered.txt', data=result['plaintext'],
                           file_name='recovered.txt', mime='text/plain')

        st.subheader('Block-by-block explanation')
        st.write('Monoalphabetic blocks use the guessed substitution table and the known rotation schedule. Caesar shifts are then determined from the next guessed plaintext letter.')
        show_blocks(result['blocks'])
        show_frequency_analysis(result['blocks'])
        validation = show_dictionary_results(result['plaintext'], dictionary_words)
        show_security_recommendations(result, validation)

        st.caption('Only A-Z letters are decrypted; spaces and punctuation remain. The original letter capitalization cannot be recovered.')
        st.caption('Made with ♡ for CSCI 462.')
