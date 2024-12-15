import os
import json
import logging
import random
import math
from typing import Dict, Any, Optional
from openai import OpenAI
from music21 import converter, stream, instrument, tempo, meter, note, midi
from dotenv import load_dotenv
from copy import deepcopy

load_dotenv()
# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Set OpenAI API key
if not os.getenv('OPENAI_API_KEY'):
    logging.error("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
    raise ValueError("OpenAI API key not found.")

# Update the OpenAI client initialization
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def determine_musical_parameters(prompt: str) -> Dict[str, Any]:
    system_prompt = """You are a professional music theorist and composer. Analyze the user's prompt and determine appropriate musical parameters for a polished, radio-ready production.

Return ONLY a valid JSON object with these parameters (no comments):
{
    "tempo": <integer between 90-140>,
    "time_signature": "<numerator>/<denominator>",
    "key": "<key letter>[m]",
    "measures": <integer between 64-128>,
    "form": "<standard song form>",
    "chord_progression": [<array of chord symbols>],
    "scale": "<scale type>",
    "style": "<musical style>"
}
"""
    try:
        response = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.5,
            top_p=0.9,
        )

        raw_response = response.choices[0].message.content.strip()
        logging.debug(f"Raw GPT response: {raw_response}")

        try:
            params = json.loads(raw_response)
        except json.JSONDecodeError:
            logging.error(f"Invalid JSON response: {raw_response}")
            return get_default_parameters()

        return validate_parameters(params)

    except Exception as e:
        logging.error(f"Error determining musical parameters: {e}")
        return get_default_parameters()

def get_default_parameters() -> Dict[str, Any]:
    return {
        'tempo': 120,
        'time_signature': '4/4',
        'key': 'C',
        'measures': 64,
        'form': 'Intro-Verse-Chorus-Verse-Chorus-Bridge-Chorus-Outro',
        'chord_progression': ['C', 'G', 'Am', 'F'],
        'scale': 'major',
        'style': 'pop'
    }

def validate_parameters(params: Dict[str, Any]) -> Dict[str, Any]:
    defaults = get_default_parameters()
    return {
        'tempo': max(90, min(params.get('tempo', defaults['tempo']), 140)),
        'time_signature': params.get('time_signature', defaults['time_signature']),
        'key': params.get('key', defaults['key']),
        'measures': max(64, min(params.get('measures', defaults['measures']), 128)),
        'form': params.get('form', defaults['form']),
        'chord_progression': params.get('chord_progression', defaults['chord_progression']),
        'scale': params.get('scale', defaults['scale']),
        'style': params.get('style', defaults['style'])
    }

def generate_music(prompt: str, params: Dict[str, Any]) -> Optional[str]:
    system_prompt = f"""You are a professional music composer creating valid ABC notation for a polished, radio-ready song. Follow these requirements strictly:

1. Compose music that follows the {params['scale']} scale and the given chord progression.
2. Style: {params['style']} with professional-level rhythmic patterns, realistic phrasing, and tasteful ornamentation.
3. Use proper voice leading and maintain cohesive thematic development.
4. Include dynamics (mp, mf, f), crescendos/decrescendos (<! !>), and articulations (staccato, legato, accents).
5. Add appropriate slurs and expression marks to enhance musicality.
6. The song form: {params['form']}. Mark each section clearly in the ABC (e.g., [I:Intro], [V:Verse], [C:Chorus]).
7. Establish a memorable melodic theme for verses and a catchy, dynamic hook for choruses.
8. Use repetition and variation to create coherence, and slight rhythmic complexity for interest.
9. Exactly {params['measures']} measures.
10. Key: {params['key']}.
11. Time Signature: {params['time_signature']}.
12. Include M:, L:, and K: headers as the first three lines after X:1.
13. Output ONLY valid ABC notation with no additional text.
14. For drum parts, use only these notes: B (bass), S (snare), H (hi-hat), O (open hi-hat), C (crash), R (ride).
"""

    try:
        response = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.7,
            top_p=0.9,
        )

        content = response.choices[0].message.content.strip()

        if any(word in content.lower() for word in ["sorry", "apologize", "here is", "here are"]):
            logging.warning("GPT response contains non-ABC content.")
            return None

        return content

    except Exception as e:
        logging.error(f"Error in generate_music: {e}")
        return None

def clean_abc(abc_notation: str) -> str:
    abc_notation = abc_notation.replace('_', 'b')
    lines = abc_notation.strip().split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if line.startswith(('M:', 'L:', 'K:', 'X:', 'T:', 'V:', '%%')):
            cleaned_lines.append(line)
            continue
        if '|' in line:
            if not line.startswith('|'):
                line = '|' + line
            if not line.endswith('|'):
                line = line + '|'
        cleaned_lines.append(line)

    abc_notation = '\n'.join(cleaned_lines)
    abc_notation = abc_notation.replace(':|', '|').replace('|:', '|')
    return abc_notation

def get_instrument_by_name(instr_name: str) -> instrument.Instrument:
    # Use instrumentFromMidiProgram to ensure compatibility
    # Choir Aahs is program 52, as per GM spec.
    # If you want a simple instrument for now, just pick a known one:
    # For example, for VoiceOohs, we use Choir Aahs (GM #52)
    instr_map = {
        'Piano': instrument.Piano(),
        'Violin': instrument.Violin(),
        'ElectricBass': instrument.ElectricBass(),
        'DrumSet': instrument.UnpitchedPercussion(),
        'SynthLead': instrument.instrumentFromMidiProgram(80),  # Lead 1 (square)
        'VoiceOohs': instrument.instrumentFromMidiProgram(52)    # Choir Aahs
    }
    return instr_map.get(instr_name, instrument.Piano())

def create_part_from_abc(abc_notation: str, instr_name: str, channel: int, params: Dict[str, Any]) -> Optional[stream.Part]:
    try:
        headers = [
            'X:1',
            f'M:{params["time_signature"]}',
            'L:1/8',
            f'K:{params["key"]}'
        ]
        
        content_lines = []
        for line in abc_notation.split('\n'):
            line = line.strip()
            if line and not line.startswith(('%', 'X:', 'M:', 'L:', 'K:', 'V:', '%%')):
                segments = line.split('"')
                filtered_line = ""
                for i, seg in enumerate(segments):
                    if i % 2 == 0:
                        filtered_line += seg
                    else:
                        pass
                if '|' in filtered_line:
                    content_lines.append(filtered_line)

        abc_data = '\n'.join(headers + content_lines)
        
        if instr_name == 'DrumSet':
            return create_drum_part(abc_data, channel)

        temp_stream = converter.parseData(abc_data, format='abc')
        part = stream.Part()
        part.id = instr_name
        
        instr = get_instrument_by_name(instr_name)
        instr.midiChannel = channel
        part.insert(0, instr)

        for elem in temp_stream.recurse():
            part.append(deepcopy(elem))

        if not part.hasMeasures():
            part.makeMeasures(inPlace=True)

        notes = list(part.recurse().getElementsByClass(['Note', 'Rest']))
        if not notes:
            return None

        for note_obj in part.recurse().notes:
            note_obj.volume.velocity = random.randint(65, 85)

        return part

    except Exception as e:
        logging.error(f"Error creating part for {instr_name}: {e}")
        return None

def create_drum_part(abc_notation: str, channel: int) -> Optional[stream.Part]:
    try:
        part = converter.parseData(abc_notation, format='abc')
        drum_part = stream.Part()
        drum_part.id = 'DrumSet'
        
        instr = instrument.UnpitchedPercussion()
        instr.midiChannel = channel
        drum_part.insert(0, instr)

        for elem in part.flatten().notesAndRests:
            drum_part.append(elem)

        return process_drum_part(drum_part)

    except Exception as e:
        logging.error(f"Error creating drum part: {e}")
        return None

def process_drum_part(part: stream.Part) -> stream.Part:
    percussion_map = {
        'C': 36,
        'D': 38,
        'E': 42,
        'F': 46,
        'G': 49,
        'A': 51,
        'B': 53,
        'z': 0
    }
    for note_obj in part.recurse().notes:
        pitch_name = note_obj.pitch.name.upper()
        midi_number = percussion_map.get(pitch_name, 35)  
        note_obj.pitch.midi = midi_number
    return part

def determine_instruments(prompt: str) -> Dict[str, Any]:
    system_prompt = """You are a music arranger for a polished, radio-ready production. Analyze the prompt and choose appropriate instruments to create a rich, balanced track.

Return ONLY a valid JSON object with instrument groups and their MIDI channels. Format:
{
    "rhythm": [["DrumSet", 10], ["ElectricBass", 1]],
    "harmony": [["Piano", 2]],
    "lead": [["SynthLead", 3]],
    "accompaniment": [["Violin", 4]],
    "backing_vocals": [["VoiceOohs", 5]]
}

DrumSet must always use channel 10.
"""

    try:
        response = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.5,
            top_p=0.9,
        )

        raw_response = response.choices[0].message.content.strip()
        cleaned_response = '\n'.join([line for line in raw_response.split('\n') 
                                      if not line.strip().startswith('//')])
        try:
            instrument_groups = json.loads(cleaned_response)
            required_groups = ['rhythm', 'harmony', 'lead']
            if not all(group in instrument_groups for group in required_groups):
                logging.warning("Missing required instrument groups, using defaults")
                return get_default_instruments()
            return instrument_groups
        except json.JSONDecodeError:
            logging.error("Invalid JSON response for instruments")
            return get_default_instruments()

    except Exception as e:
        logging.error(f"Error determining instruments: {e}")
        return get_default_instruments()

def get_default_instruments() -> Dict[str, Any]:
    return {
        "rhythm": [["DrumSet", 10], ["ElectricBass", 1]],
        "harmony": [["Piano", 2]],
        "lead": [["SynthLead", 3]],
        "accompaniment": [["Violin", 4]],
        "backing_vocals": [["VoiceOohs", 5]]
    }

def generate_part(user_prompt: str, instr: str, channel: int, params: Dict[str, Any]) -> Optional[stream.Part]:
    if instr == 'DrumSet':
        instrument_prompt = (
            f"Craft {params['measures']} measures of professional drum patterns in {params['time_signature']} for a {params['style']} style song, following {params['chord_progression']} and {params['form']}. "
            "Use tasteful variations, realistic fills, and appropriate dynamics. Only use B,S,H,O,C,R notes."
        )
    else:
        base_prompt = (
            f"Craft {params['measures']} measures of a {instr} part for a {params['style']} song. "
            f"Key: {params['key']}, Time: {params['time_signature']}, Form: {params['form']} with chord progression {params['chord_progression']}. "
            "Include dynamics, articulations, and tasteful melodic/harmonic content. Make the result professional, cohesive, and radio-ready."
        )

        instrument_prompt = (
            f"{base_prompt}\n"
            "Ensure M:, L:, and K: headers are present at the start, and produce ONLY ABC notation."
        )

    abc_notation = generate_music(instrument_prompt, params)
    if not abc_notation:
        logging.warning(f"No ABC notation generated for {instr}")
        return None

    logging.info(f"\nABC notation for {instr}:\n{abc_notation}")

    # Replace [V:Something] lines with V:1
    lines = abc_notation.split('\n')
    processed = []
    for line in lines:
        if line.strip().startswith('[V:'):
            line = "V:1"
        processed.append(line)
    abc_notation = '\n'.join(processed)

    abc_notation = clean_abc(abc_notation)
    if not abc_notation:
        logging.warning(f"Failed to clean ABC notation for {instr}")
        return None

    part = create_part_from_abc(abc_notation, instr, channel, params)
    if not part:
        logging.warning(f"Failed to create part for {instr}")
        return None
    if instr == 'DrumSet':
        part = process_drum_part(part)

    notes = list(part.recurse().getElementsByClass(['Note', 'Rest']))
    if not notes:
        logging.warning(f"No notes found in part for {instr}")
        return None

    # Section-based velocity shaping
    form = params['form'].lower()
    verse_words = ["verse"]
    chorus_words = ["chorus", "hook"]
    bridge_words = ["bridge", "pre-chorus"]
    total_measures = params['measures']
    sections = form.split('-')
    section_len = max(1, total_measures // len(sections))
    measure_count = 0

    for m in part.getElementsByClass('Measure'):
        current_section = sections[measure_count // section_len] if (measure_count // section_len) < len(sections) else sections[-1]
        current_section_lower = current_section.lower()

        if any(s in current_section_lower for s in verse_words):
            vel_min, vel_max = 60, 75
        elif any(s in current_section_lower for s in chorus_words):
            vel_min, vel_max = 80, 100
        elif any(s in current_section_lower for s in bridge_words):
            vel_min, vel_max = 70, 85
        else:
            vel_min, vel_max = 65, 85

        for n in m.notes:
            n.volume.velocity = random.randint(vel_min, vel_max)
            if n.offset is not None and n.offset > 0:
                n.offset += random.uniform(-0.02, 0.02)

        measure_count += 1

    return part

def create_song(user_prompt: str) -> Optional[stream.Score]:
    try:
        global_parameters = determine_musical_parameters(user_prompt)
        logging.info("\nSelected musical parameters:")
        for param, value in global_parameters.items():
            logging.info(f"{param}: {value}")

        score = stream.Score()

        score.insert(0, tempo.MetronomeMark(number=global_parameters['tempo']))
        score.insert(0, meter.TimeSignature(global_parameters['time_signature']))

        instrument_groups = determine_instruments(user_prompt)
        logging.info(f"\nSelected instruments: {instrument_groups}")

        valid_parts = 0
        for group, instruments_ in instrument_groups.items():
            for instr_name, channel in instruments_:
                logging.info(f"\nGenerating {instr_name} part ({group} group) on channel {channel}...")
                part = generate_part(user_prompt, instr_name, channel, global_parameters)
                if part and len(part.flatten().notesAndRests) > 0:
                    if not part.hasMeasures():
                        part.makeMeasures(inPlace=True)
                    score.append(part)
                    valid_parts += 1

        if valid_parts == 0:
            logging.error("No valid parts were generated!")
            return None

        if not score.hasMeasures():
            score.makeMeasures(inPlace=True)
        score = score.expandRepeats()

        return score

    except Exception as e:
        logging.error(f"Error generating song: {e}")
        return None

def main():
    try:
        user_song_prompt = input("Enter a prompt to generate your song: ")
        if not user_song_prompt.strip():
            logging.error("No prompt provided. Exiting.")
            return

        song = create_song(user_song_prompt)
        if song:
            midi_file = 'generated_song.mid'
            song.write('midi', fp=midi_file)
            logging.info(f"MIDI file '{midi_file}' generated successfully!")
        else:
            logging.error("Failed to generate song - no valid content")
    except Exception as e:
        logging.error(f"Error generating MIDI file: {e}")

if __name__ == "__main__":
    main()
