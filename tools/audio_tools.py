import opensmile
import librosa
import numpy as np
import scipy.io.wavfile as wavfile
import os
import time
import threading

SAMPLE_RATE = 16000
CHANNELS = 1
AUDIO_FILE = "data/temp_audio/user_input.wav"

def record_user_input(duration=8):
    os.makedirs(os.path.dirname(AUDIO_FILE), exist_ok=True)

    frames = []

    def callback(indata, frames_count, time_info, status):
        if status:
            print(f"InputStream status: {status}")
        # copy the buffer since the memory gets reused by sounddevice
        frames.append(indata.copy())

    stop_event = threading.Event()
    stopper_input = {'value': None}

    def stopper():
        try:
            # User can press Enter to stop recording early, or type a command to stop the session
            inp = input("Recording... press Enter to stop early, or type 'quit' to end the session:\n")
            stopper_input['value'] = inp
        except Exception:
            stopper_input['value'] = None
        finally:
            stop_event.set()

    stopper_thread = threading.Thread(target=stopper, daemon=True)
    stopper_thread.start()

    print(f"Recording for up to {duration} seconds. Press Enter to stop early or type 'quit' to stop the session.")
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, callback=callback, dtype='float32'):
        start_time = time.time()
        while not stop_event.is_set() and (time.time() - start_time) < duration:
            time.sleep(0.1)

    # Determine if the user requested to stop the entire session
    user_cmd = stopper_input.get('value')
    stop_session = False
    if isinstance(user_cmd, str) and user_cmd.strip().lower() in {"quit", "exit", "stop", "end"}:
        stop_session = True

    if not frames:
        print("No audio captured.")
        return (None, stop_session)

    audio_np = np.concatenate(frames, axis=0)

    if np.issubdtype(audio_np.dtype, np.floating):
        audio_int16 = (audio_np * np.iinfo(np.int16).max).astype('int16')
    else:
        audio_int16 = audio_np

    timestamp = int(time.time() * 1000)
    filename = f"data/temp_audio/user_input_{timestamp}.wav"
    wavfile.write(filename, SAMPLE_RATE, audio_int16)
    print(f"Recording saved to {filename}")
    return (filename, stop_session)

def extract_vocal_biomarkers(audio_file_path):
    try:
        extractor = opensmile.Smile(
            feature_set=opensmile.FeatureSet.eGeMAPSv02,
            feature_level=opensmile.FeatureLevel.Functionals,
        )
        result_df = extractor.process_file(audio_file_path)
        metrics = {
            "f0_mean": result_df['f0semitone_sma3nz_amean'].iloc[0],
            "f0_stddev": result_df['f0semitone_sma3nz_stddevNorm'].iloc[0],
            "jitter_local": result_df['jitterLocal_sma3nz_amean'].iloc[0],
            "shimmer_local": result_df['shimmerLocal_sma3nz_amean'].iloc[0],
            "loudness_mean": result_df['loudness_sma3_amean'].iloc[0],
            "loudness_stddev": result_df['loudness_sma3_stddevNorm'].iloc[0],
            "speaking_rate": result_df['speakingRate_sma3nz_amean'].iloc[0],
        }
        metrics["vocal_stability_score"] = 1 - metrics.get("jitter_local", 0)
        for key, value in list(metrics.items()):
            try:
                if np.isnan(value):
                    metrics[key] = 0.0
            except Exception:
                pass
        return metrics
    except Exception as e:
        print(f"Error during biomarker extraction: {e}")
        return {
            "f0_mean": 0.0,
            "jitter_local": 0.0,
            "loudness_mean": 0.0,
            "error": str(e)
        }

if __name__ == '__main__':
    print("Testing Audio Tools")
    recorded_file, session_active = record_user_input(duration=5)
    if session_active:
        print("Session ended by user.")
    else:
        biomarkers = extract_vocal_biomarkers(recorded_file)
        print("Extracted Vocal Biomarkers")
        for key, value in biomarkers.items():
            try:
                print(f"  {key:<20}: {value:.4f}")
            except Exception:
                print(f"  {key:<20}: {value}")
