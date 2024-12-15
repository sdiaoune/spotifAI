### README

# Music Generation Script

This script generates MIDI music compositions based on user prompts, leveraging OpenAI's GPT models and the `music21` library for music representation. It creates radio-ready tracks with cohesive arrangements, structured musical forms, and dynamic instrument parts.

---

## Features
- **Dynamic Prompt Parsing**: Converts text prompts into detailed musical parameters like tempo, key, and chord progressions.
- **Instrument Arrangement**: Assigns appropriate instruments based on the musical style and user input.
- **ABC Notation Support**: Generates and parses music in ABC notation for streamlined music creation.
- **MIDI File Output**: Exports the composed music as a MIDI file for use in digital audio workstations (DAWs) or other software.

---

## Requirements

### Python Libraries
- `os`
- `json`
- `logging`
- `random`
- `math`
- `dotenv`
- `music21`
- `openai`

### Installation
1. Install dependencies:
   ```bash
   pip install openai python-dotenv music21
   ```
2. Set up the `.env` file with your OpenAI API key:
   ```env
   OPENAI_API_KEY=your-api-key
   ```

---

## How It Works

1. **User Prompt**:
   - Enter a text description of the desired music (e.g., "A fast-paced electronic track with a catchy hook").
2. **Music Parameter Extraction**:
   - The script uses OpenAI's GPT model to extract musical parameters such as tempo, key, scale, and structure.
3. **ABC Notation Generation**:
   - Generates music parts (lead, harmony, rhythm) using ABC notation.
4. **MIDI Composition**:
   - Converts the generated music into MIDI format using `music21`.
5. **Output**:
   - Saves the composed music as a `generated_song.mid` file.

---

## Key Functions

### `determine_musical_parameters(prompt: str)`
- Extracts tempo, key, time signature, chord progressions, and song form from the user prompt.

### `generate_music(prompt: str, params: Dict[str, Any])`
- Creates ABC notation based on the musical parameters and user input.

### `create_part_from_abc(abc_notation: str, instr_name: str, channel: int, params: Dict[str, Any])`
- Converts ABC notation into a `music21` part for a specific instrument.

### `create_song(user_prompt: str)`
- Combines all musical parts into a complete song, exports it to MIDI format.

---

## Usage

1. **Run the Script**:
   ```bash
   python script_name.py
   ```
2. **Enter Your Prompt**:
   Provide a text description of the music you want to generate.
3. **Get Your MIDI File**:
   The script outputs a MIDI file named `generated_song.mid` in the current directory.

---

## Example

**Prompt**:
```
A slow, emotional ballad with piano and violin, in A minor, with a time signature of 3/4.
```

**Output**:
- A MIDI file with a structured composition featuring piano and violin parts.

---

## Logging

- Logs are saved to the console for debugging and monitoring the generation process.
- Log levels include `INFO` and `ERROR`.

---

## Limitations
- Requires an active OpenAI API key.
- Output quality depends on the GPT model and prompt clarity.
- Requires basic knowledge of music theory to interpret parameters effectively.

---

## Troubleshooting

### Common Issues
- **No API Key**:
  - Ensure the `.env` file contains the correct API key.
- **Empty Output**:
  - Refine the input prompt for better results.
- **Dependencies Missing**:
  - Install required Python libraries as specified above.

---

## Contributing
Feel free to submit issues or pull requests on GitHub to improve the script.

---

## License
This project is licensed under the MIT License.

